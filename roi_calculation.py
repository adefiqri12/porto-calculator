# Getting user inputs for the initial capital, monthly return rate, and compounding periods.
initial_capital = float(input("Enter the initial capital in dollars: "))
monthly_return_rate = float(input("Enter the monthly return rate (in decimal form, e.g., 0.30 for 30%): "))
compounding_periods = int(input("Enter the number of compounding periods in a year: "))

# Calculating the future value after the specified period.
future_value = initial_capital * (1 + monthly_return_rate) ** compounding_periods

# Calculating the ROI in percentage.
roi = ((future_value - initial_capital) / initial_capital) * 100  # ROI in percentage

# Printing all variables and results.
print("Initial Capital: $", initial_capital)
print("Monthly Return Rate:", monthly_return_rate * 100, "%")
print("Compounding Periods (Months in a Year):", compounding_periods)
print(f"Future Value after {compounding_periods} Years: ${round(future_value, 2)}")
print("Annual ROI: ", round(roi, 2), "%")