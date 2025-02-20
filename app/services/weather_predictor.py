import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import Counter
from statistics import mean, stdev

class WeatherPredictor:
    def __init__(self, api_key: str):
        """Initialize the weather predictor with API key."""
        self.api_key = api_key
        self.base_url = "https://api.weatherstack.com/historical"
        self.start_year = 2015

    def generate_trip_dates(self, start_date: str, end_date: str) -> List[str]:
        """Generate list of dates between start and end date."""
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        dates = []
        
        current_dt = start_dt
        while current_dt <= end_dt:
            dates.append(current_dt.strftime('%Y-%m-%d'))
            current_dt += timedelta(days=1)
            
        return dates

    def generate_historical_dates(self, target_date: str) -> List[str]:
        """Generate list of historical dates to analyze for the exact target date in past years."""
        target_dt = datetime.strptime(target_date, '%Y-%m-%d')
        current_year = datetime.now().year
        dates = []
        
        for year in range(self.start_year, current_year):
            historical_date = target_dt.replace(year=year)
            dates.append(historical_date.strftime('%Y-%m-%d'))
        
        return sorted(dates)

    def fetch_historical_data(self, location: str, dates: List[str]) -> Dict:
        """Fetch historical weather data for multiple dates in a single API request."""
        params = {
            "access_key": self.api_key,
            "query": location,
            "historical_date": ";".join(dates),
            "hourly": "1"
        }
        
        response = requests.get(self.base_url, params=params)
        if response.status_code != 200:
            raise Exception(f"API request failed with status {response.status_code}")
        return response.json()

    def get_training_data(self, location: str, target_date: str) -> List[Dict]:
        """Collect historical training data in a single API request."""
        historical_dates = self.generate_historical_dates(target_date)
        
        try:
            data = self.fetch_historical_data(location, historical_dates)
        except Exception as e:
            print(f"Error fetching data: {str(e)}")
            return []

        training_data = []
        for date in historical_dates:
            if 'historical' in data and date in data['historical']:
                historical = data['historical'][date]
                hourly_data = historical.get('hourly', [])
                
                descriptions = [
                    hour['weather_descriptions'][0]
                    for hour in hourly_data
                    if hour.get('weather_descriptions')
                ]
                
                training_data.append({
                    'date': date,
                    'min_temp': historical['mintemp'],
                    'max_temp': historical['maxtemp'],
                    'avg_temp': historical['avgtemp'],
                    'uv_index': historical['uv_index'],
                    'descriptions': descriptions,
                    'year': int(date[:4])
                })
        
        return training_data

    def _predict_temperatures(self, training_data: List[Dict]) -> Dict:
        """Predict temperatures using simple averages."""
        if not training_data:
            return {'min': None, 'max': None}
        
        min_temps = [data['min_temp'] for data in training_data]
        max_temps = [data['max_temp'] for data in training_data]
        
        return {
            'min': mean(min_temps),
            'max': mean(max_temps)
        }
    
    def _predict_uv_index(self, training_data: List[Dict]) -> float:
        """Predict UV index using simple average."""
        if not training_data:
            return None
        
        uv_indexes = [data['uv_index'] for data in training_data]
        return mean(uv_indexes)
    
    def _predict_description(self, training_data: List[Dict]) -> str:
        """Predict the most common weather description."""
        all_descriptions = []
        for data in training_data:
            all_descriptions.extend(data['descriptions'])
        
        if not all_descriptions:
            return "No prediction available"
        
        description_counts = Counter(all_descriptions)
        return description_counts.most_common(1)[0][0]
    
    def _calculate_confidence(self, training_data: List[Dict]) -> float:
        """Calculate confidence score based on data consistency."""
        if not training_data:
            return 0.0
        
        temp_variation = stdev([data['avg_temp'] for data in training_data]) if len(training_data) > 1 else 0
        temp_confidence = 1 / (1 + temp_variation / 10)
        
        return round(temp_confidence, 2)

    def predict_trip_weather(self, location: str, start_date: str, end_date: Optional[str] = None) -> Dict:
        """Predict weather for a trip period."""
        # If end_date is not provided, use start_date for a single-day trip
        trip_dates = [start_date] if end_date is None else self.generate_trip_dates(start_date, end_date)
        all_training_data = []
        
        # Collect training data for each day in the trip
        for date in trip_dates:
            training_data = self.get_training_data(location, date)
            all_training_data.extend(training_data)
        
        if not all_training_data:
            raise Exception("No historical data available for prediction")

        # Calculate aggregate predictions
        temp_predictions = self._predict_temperatures(all_training_data)
        uv_prediction = self._predict_uv_index(all_training_data)
        weather_description = self._predict_description(all_training_data)

        return {
            'trip_start': start_date,
            'trip_end': end_date if end_date else start_date,
            'predicted_min_temp': round(temp_predictions['min'], 1),
            'predicted_max_temp': round(temp_predictions['max'], 1),
            'predicted_uv_index': round(uv_prediction, 1),
            'predicted_description': weather_description,
            'confidence_score': self._calculate_confidence(all_training_data),
            'years_analyzed': sorted(set(data['year'] for data in all_training_data)),
            'days_analyzed': len(trip_dates)
        }