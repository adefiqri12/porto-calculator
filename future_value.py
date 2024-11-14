import csv
from datetime import datetime

def calculate_future_value():
    try:
        monthly_investment = float(input("Enter your monthly investment amount: Rp"))
        annual_roi = float(input("Enter annual ROI (%): "))
        total_months = int(input("Enter total number of months: "))
        save_details = input("Would you like to save yearly details to CSV? (y/n): ").lower()
        
        # Convert annual ROI to monthly rate
        monthly_rate = (annual_roi / 100) / 12
        
        # Calculate final future value
        future_value = monthly_investment * ((pow(1 + monthly_rate, total_months) - 1) / monthly_rate) * (1 + monthly_rate)
        
        # Calculate total investment
        total_investment = monthly_investment * total_months
        
        # Calculate total return
        total_return = future_value - total_investment
        
        # Display summary results
        print("\n=== Investment Summary ===")
        print(f"Monthly Investment: Rp{monthly_investment:,.2f}")
        print(f"Annual ROI: {annual_roi}%")
        print(f"Investment Period: {total_months} months ({total_months/12:.1f} years)")
        print(f"\nTotal Investment: Rp{total_investment:,.2f}")
        print(f"Total Return: Rp{total_return:,.2f}")
        print(f"Future Value: Rp{future_value:,.2f}")
        
        # Calculate and save yearly details if requested
        if save_details == 'y':
            yearly_details = []
            current_value = 0
            yearly_investment = monthly_investment * 12
            
            for year in range(1, int(total_months/12) + 1):
                # Calculate values for this year
                start_value = current_value
                
                # Calculate cumulative investment up to this year
                cumulative_investment = yearly_investment * year
                
                # Calculate end of year value
                current_value = monthly_investment * (
                    (pow(1 + monthly_rate, year * 12) - 1) / monthly_rate
                ) * (1 + monthly_rate)
                
                # Calculate interest earned this year
                if year == 1:
                    interest_earned = current_value - yearly_investment
                else:
                    interest_earned = current_value - start_value - yearly_investment
                
                yearly_details.append({
                    'Year': year,
                    'Cumulative_Investment': cumulative_investment,
                    'Interest_Earned': interest_earned,
                    'Total_Value': current_value
                })
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"investment_details_{timestamp}.csv"
            
            # Save to CSV
            with open(filename, 'w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=[
                    'Year', 
                    'Cumulative_Investment', 
                    'Interest_Earned', 
                    'Total_Value'
                ])
                writer.writeheader()
                for row in yearly_details:
                    writer.writerow({
                        'Year': row['Year'],
                        'Cumulative_Investment': f"{row['Cumulative_Investment']:,.2f}",
                        'Interest_Earned': f"{row['Interest_Earned']:,.2f}",
                        'Total_Value': f"{row['Total_Value']:,.2f}"
                    })
            print(f"\nYearly details have been saved to {filename}")
            
    except ValueError:
        print("Please enter valid numerical values!")

# Run the program
if __name__ == "__main__":
    print("Future Value Calculator - Monthly Investment")
    print("-------------------------------------------")
    calculate_future_value()