import pandas as pd
import numpy as np
import pywt
from typing import Tuple, List

class PricePredictor:
    def __init__(self):
        self.wavelet = 'db1'  # Daubechies 1 wavelet
        self.level = 3        # Decomposition level
        self.window_size = 60 # Analysis window (1 hour)
        
    def decompose_signal(self, data: np.ndarray) -> Tuple[np.ndarray, List[np.ndarray]]:
        """Perform wavelet decomposition on price data"""
        coeffs = pywt.wavedec(data, self.wavelet, level=self.level)
        return coeffs[0], coeffs[1:]
    
    def detect_trend_change(self, approximation: np.ndarray, details: List[np.ndarray]) -> float:
        """
        Analyze wavelet coefficients to detect potential trend changes
        Returns probability of trend reversal
        """
        # Check if we have enough data
        if len(approximation) < 10:
            return 0.0
            
        # Analyze the approximation coefficient (main trend)
        trend_direction = np.diff(approximation[-5:]).mean()
        
        # Analyze detail coefficients (high-frequency components)
        detail_energies = [np.abs(d[-5:]).mean() for d in details]
        
        # Higher energy in detail coefficients suggests potential reversal
        total_energy = sum(detail_energies)
        energy_ratio = detail_energies[0] / total_energy if total_energy > 0 else 0
        
        # Combine signals
        if trend_direction < 0 and energy_ratio > 0.5:
            # Downtrend with high short-term energy suggests potential reversal
            return min(1.0, energy_ratio * 1.5)
        
        return 0.0
    
    def predict(self, df: pd.DataFrame) -> float:
        """Predict probability of trend reversal"""
        if len(df) < self.window_size:
            return 0.0
            
        # Get recent price data
        prices = df['close'].values[-self.window_size:]
        
        # Normalize prices to improve wavelet analysis
        normalized_prices = (prices - prices.mean()) / prices.std()
        
        # Perform wavelet decomposition
        approximation, details = self.decompose_signal(normalized_prices)
        
        # Detect potential trend change
        reversal_probability = self.detect_trend_change(approximation, details)
        
        return reversal_probability
    
    def train(self, df: pd.DataFrame):
        """No training needed for wavelet analysis"""
        pass