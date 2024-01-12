import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import StandardScaler
import numpy as np
import calendar
from datetime import datetime, timedelta

# Function to find the closest previous saldo to a given date
def get_closest_previous_saldo(data, target_date):
    if target_date in data.index:
        return data['Saldo'].at[target_date]
    else:
        previous_dates = data.index[data.index < target_date]
        if not previous_dates.empty:
            closest_date = previous_dates[-1]
            return data['Saldo'].at[closest_date]
        else:
            return 0

# Function to predict saldo for the last day of the current month
def predict_last_day_of_current_month(model, data, scaler):
    today = datetime.today()
    start_of_month = today.replace(day=1)
    current_month_saldo = get_closest_previous_saldo(data, start_of_month)
    days_remaining = calendar.monthrange(today.year, today.month)[1] - today.day

    # Prepare future dates for prediction
    future_dates = pd.DataFrame({
        'DayOfMonth': [today.day + i for i in range(days_remaining)],
        'DayOfWeek': [(today + timedelta(days=i)).weekday() for i in range(days_remaining)],
        'Month': today.month,
        'WeekOfYear': [(today + timedelta(days=i)).isocalendar().week for i in range(days_remaining)]
    })

    future_dates_scaled = scaler.transform(future_dates)  # Scale the features
    future_changes = model.predict(future_dates_scaled)
    end_of_month_saldo = current_month_saldo + np.sum(future_changes)
    return round(end_of_month_saldo, 2)

# Load and preprocess data
data = pd.read_csv('/home/PI/saldo_data.csv', delimiter=',')
data.drop_duplicates(inplace=True)
data['Date'] = pd.to_datetime(data['Date'])
data.set_index('Date', inplace=True)
data.sort_index(inplace=True)
data['DailyChange'] = data['Saldo'].diff()
data['DailyChange'].fillna(data['Saldo'].iloc[0], inplace=True)

# Adding more features
data['Month'] = data.index.month
data['WeekOfYear'] = data.index.isocalendar().week

# Define features and target variable
X = data[['DayOfMonth', 'DayOfWeek', 'Month', 'WeekOfYear']]
y = data['DailyChange']

# Scaling features
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

# Define and train the model with hyperparameter tuning
model = RandomForestRegressor(random_state=42)
param_grid = {'n_estimators': [100, 200], 'max_depth': [None, 10, 20]}
grid_search = GridSearchCV(model, param_grid, cv=5)
grid_search.fit(X_train, y_train)

# Optimal model
optimal_model = grid_search.best_estimator_

# Cross-validation score
cv_scores = cross_val_score(optimal_model, X_train, y_train, cv=5)
print("Average CV Score:", np.mean(cv_scores))

# Make predictions and evaluate the model
predictions = optimal_model.predict(X_test)
print("RMSE:", np.sqrt(mean_squared_error(y_test, predictions)))

# Predict end-of-month saldo
prediction = predict_last_day_of_current_month(optimal_model, data, scaler)
print("End of current month prediction:", prediction)
