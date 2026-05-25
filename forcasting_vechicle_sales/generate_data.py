import numpy as np
import pandas as pd

np.random.seed(42)

n_samples = 5000

manufacturers = ['Toyota', 'Honda', 'Ford', 'Chevrolet', 'BMW', 'Mercedes-Benz', 'Audi', 'Hyundai', 'Kia', 'Volkswagen']
models = {
    'Toyota': ['Camry', 'Corolla', 'RAV4', 'Highlander', 'Prius'],
    'Honda': ['Civic', 'Accord', 'CR-V', 'HR-V', 'Fit'],
    'Ford': ['F-150', 'Escape', 'Explorer', 'Focus', 'Mustang'],
    'Chevrolet': ['Silverado', 'Equinox', 'Malibu', 'Tahoe', 'Camaro'],
    'BMW': ['3 Series', '5 Series', 'X3', 'X5', '7 Series'],
    'Mercedes-Benz': ['C-Class', 'E-Class', 'GLC', 'GLE', 'S-Class'],
    'Audi': ['A4', 'A6', 'Q5', 'Q7', 'TT'],
    'Hyundai': ['Elantra', 'Sonata', 'Tucson', 'Santa Fe', 'Accent'],
    'Kia': ['Forte', 'Optima', 'Sportage', 'Sorento', 'Rio'],
    'Volkswagen': ['Jetta', 'Passat', 'Tiguan', 'Atlas', 'Golf']
}
vehicle_types = ['Sedan', 'SUV', 'Truck', 'Coupe', 'Hatchback']
fuel_types = ['Gasoline', 'Diesel', 'Hybrid', 'Electric']
transmission_types = ['Automatic', 'Manual', 'CVT']
regions = ['North', 'South', 'East', 'West', 'Central']

manufacturer = np.random.choice(manufacturers, n_samples)
model = np.array([np.random.choice(models[m]) for m in manufacturer])
vehicle_type = np.random.choice(vehicle_types, n_samples, p=[0.35, 0.30, 0.15, 0.10, 0.10])
fuel_type = np.random.choice(fuel_types, n_samples, p=[0.50, 0.15, 0.25, 0.10])
transmission = np.random.choice(transmission_types, n_samples, p=[0.60, 0.25, 0.15])
region = np.random.choice(regions, n_samples)

year = np.random.randint(2015, 2024, n_samples)
engine_size = np.random.uniform(1.0, 6.0, n_samples).round(1)
horsepower = np.random.randint(100, 500, n_samples)
mpg = np.random.uniform(15, 55, n_samples).round(1)
price = np.random.uniform(15000, 80000, n_samples).round(0)
mileage = np.random.randint(0, 150000, n_samples)

age = 2024 - year

base_price_effect = -0.0001 * price
age_effect = -150 * age
mileage_effect = -0.08 * mileage
mpg_effect = 300 * mpg
horsepower_effect = 50 * horsepower

fuel_effect = np.where(fuel_type == 'Electric', 5000, 
                      np.where(fuel_type == 'Hybrid', 3000, 
                              np.where(fuel_type == 'Diesel', -2000, 0)))

region_effect = np.where(region == 'West', 2000,
                        np.where(region == 'East', 1500,
                                np.where(region == 'South', 1000,
                                        np.where(region == 'North', 500, 0))))

vehicle_type_effect = np.where(vehicle_type == 'SUV', 3000,
                              np.where(vehicle_type == 'Truck', 2500,
                                      np.where(vehicle_type == 'Coupe', -1000, 0)))

noise = np.random.normal(0, 2000, n_samples)

sales = (base_price_effect + age_effect + mileage_effect + mpg_effect + 
         horsepower_effect + fuel_effect + region_effect + vehicle_type_effect + noise).round(0)

sales = np.maximum(sales, 100)
sales = np.minimum(sales, 50000)

df = pd.DataFrame({
    'Manufacturer': manufacturer,
    'Model': model,
    'Vehicle_Type': vehicle_type,
    'Fuel_Type': fuel_type,
    'Transmission': transmission,
    'Region': region,
    'Year': year,
    'Engine_Size': engine_size,
    'Horsepower': horsepower,
    'MPG': mpg,
    'Price': price,
    'Mileage': mileage,
    'Age': age,
    'Sales': sales
})

df.to_csv('car_sales_data.csv', index=False)
print("数据集已生成: car_sales_data.csv")
print(f"数据规模: {df.shape}")
print("\n数据集前5行:")
print(df.head())