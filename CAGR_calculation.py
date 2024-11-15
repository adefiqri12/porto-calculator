return_all_of_time = float(input("Return all of time (%): "))
return_all_of_time = return_all_of_time/100
all_of_time_years = int(input("All of time years: "))

CAGR = pow(return_all_of_time + 1, 1/all_of_time_years) - 1 
print(f"CAGR: {round(CAGR*100,3)}%")