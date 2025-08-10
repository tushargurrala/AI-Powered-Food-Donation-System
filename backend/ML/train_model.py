import joblib
import numpy as np
from sklearn.linear_model import LinearRegression

# Dummy training data
X = np.array([[1, 10], [2, 20], [3, 30], [4, 40], [5, 50]])
y = np.array([5, 10, 15, 20, 25])

model = LinearRegression()
model.fit(X, y)

joblib.dump(model, "food_donation_predictor.pkl")
print("Model trained and saved!")
