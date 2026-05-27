import json 
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from typing import Union
from prod_info import products
from helpers import generate_product_description, find_nearest_metro_city, get_unique_id
import pandas as pd
import os
from datetime import datetime
from geopy.distance import geodesic

# Static pincode to city mapping
PINCODE_CITY_MAP = {
    "110001": "Delhi",
    "110002": "Delhi",
    "110003": "Delhi",
    "400001": "Mumbai",
    "400002": "Mumbai",
    "400003": "Mumbai",
    "560001": "Bangalore",
    "560002": "Bangalore",
    "560003": "Bangalore",
    "411001": "Pune",
    "411002": "Pune",
    "411003": "Pune",
    "700001": "Kolkata",
    "700002": "Kolkata",
    "700003": "Kolkata",
    "600001": "Chennai",
    "600002": "Chennai",
    "600003": "Chennai",
    "500001": "Hyderabad",
    "500002": "Hyderabad",
    "500003": "Hyderabad",
    "380001": "Ahmedabad",
    "380002": "Ahmedabad",
    "380003": "Ahmedabad",
    "122001": "Gurgaon",
    "122002": "Gurgaon",
}

# Warehouse location (Delhi headquarters)
WAREHOUSE_COORDS = (28.6139, 77.2090)

# Static pincode to coordinates mapping (for fast distance calculation)
PINCODE_COORDS_MAP = {
    "110001": (28.6139, 77.2090),  # Delhi
    "110002": (28.6139, 77.2090),  # Delhi
    "110003": (28.6139, 77.2090),  # Delhi
    "400001": (18.9388, 72.8354),  # Mumbai
    "400002": (18.9388, 72.8354),  # Mumbai
    "400003": (18.9388, 72.8354),  # Mumbai
    "560001": (12.9716, 77.5946),  # Bangalore
    "560002": (12.9716, 77.5946),  # Bangalore
    "560003": (12.9716, 77.5946),  # Bangalore
    "411001": (18.5204, 73.8567),  # Pune
    "411002": (18.5204, 73.8567),  # Pune
    "411003": (18.5204, 73.8567),  # Pune
    "700001": (22.5726, 88.3639),  # Kolkata
    "700002": (22.5726, 88.3639),  # Kolkata
    "700003": (22.5726, 88.3639),  # Kolkata
    "600001": (13.0827, 80.2707),  # Chennai
    "600002": (13.0827, 80.2707),  # Chennai
    "600003": (13.0827, 80.2707),  # Chennai
    "500001": (17.3850, 78.4867),  # Hyderabad
    "500002": (17.3850, 78.4867),  # Hyderabad
    "500003": (17.3850, 78.4867),  # Hyderabad
    "380001": (23.0225, 72.5714),  # Ahmedabad
    "380002": (23.0225, 72.5714),  # Ahmedabad
    "380003": (23.0225, 72.5714),  # Ahmedabad
    "122001": (28.4595, 77.0266),  # Gurgaon
    "122002": (28.4595, 77.0266),  # Gurgaon
}

def get_delivery_coords(pincode: str):
    """Get coordinates for a pincode using static map"""
    return PINCODE_COORDS_MAP.get(pincode, WAREHOUSE_COORDS)

def calculate_shipping_cost(distance_km: float) -> dict:
    """Calculate shipping cost and delivery days based on distance"""
    base_shipping = 50  # Base shipping in rupees
    per_km_rate = 2    # Rupees per km
    
    shipping_cost = base_shipping + (distance_km * per_km_rate)
    
    # Delivery tiers based on distance
    if distance_km <= 50:
        delivery_days = 2
    elif distance_km <= 200:
        delivery_days = 3
    elif distance_km <= 500:
        delivery_days = 4
    else:
        delivery_days = 6
    
    return {
        "shipping_cost": round(shipping_cost),
        "delivery_days": delivery_days,
        "distance_km": round(distance_km, 2)
    }

# Define tools for the agent
@tool
def show_all_products():
    """Show all available furniture products with their IDs and names"""
    product_list = []
    for product_id, product_info in products.items():
        product_list.append({
            "id": product_id,
            "name": product_info["name"],
            "price": f"₹{product_info['MRP']}"
        })
    return product_list

@tool
def get_product_details(product_id: str):
    """Get detailed information about a specific product by ID"""
    if product_id in products:
        return products[product_id]
    return f"Product with ID {product_id} not found"

@tool
def get_product_description(product_id: str):
    """Generate a customer-friendly description for a product"""
    try:
        return generate_product_description(product_id)
    except Exception as e:
        return f"Error generating description: {str(e)}"

@tool
def find_delivery_city(pincode: str):
    """Find the nearest metro city for delivery based on pincode"""
    try:
        result = find_nearest_metro_city(pincode)
        if isinstance(result, tuple):
            return {"nearest_city": result[1], "city_pincode": result[0]}
        return result
    except Exception as e:
        return f"Error finding delivery city: {str(e)}"

@tool
def generate_booking_id():
    """Generate a unique booking ID for new orders"""
    return get_unique_id()

@tool
def process_order(product_id: str, quantity: Union[int, str], address: str, delivery_pincode: str):
    """Process and confirm a furniture order with booking ID, dynamic delivery costs and timelines"""
    try:
        # Convert quantity to int if it's a string
        quantity = int(quantity)
        
        # Get product details
        if product_id not in products:
            return {"success": False, "message": f"Product {product_id} not found"}
        
        product = products[product_id]
        unit_price = product["MRP"]
        product_total = unit_price * quantity
        
        # Get delivery city
        delivery_city = PINCODE_CITY_MAP.get(delivery_pincode, "Nearest Metro City")
        
        # Calculate shipping based on distance
        delivery_coords = get_delivery_coords(delivery_pincode)
        distance_km = geodesic(WAREHOUSE_COORDS, delivery_coords).kilometers
        shipping_info = calculate_shipping_cost(distance_km)
        
        shipping_cost = shipping_info["shipping_cost"]
        delivery_days = shipping_info["delivery_days"]
        
        # Calculate final total
        total_price = product_total + shipping_cost
        
        # Generate booking ID
        booking_id = get_unique_id()
        
        # Prepare booking data for CSV
        booking_data = {
            "booking_id": booking_id,
            "product_id": product_id,
            "product_name": product["name"],
            "quantity": quantity,
            "unit_price": unit_price,
            "product_total": product_total,
            "distance_km": distance_km,
            "shipping_cost": shipping_cost,
            "total_price": total_price,
            "delivery_city": delivery_city,
            "delivery_address": address,
            "delivery_pincode": delivery_pincode,
            "estimated_delivery_days": delivery_days,
            "status": "Order Confirmed",
            "order_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Save to Bookings.csv
        csv_file = "Bookings.csv"
        try:
            if os.path.exists(csv_file):
                df = pd.read_csv(csv_file)
            else:
                df = pd.DataFrame(columns=booking_data.keys())
            
            df.loc[len(df)] = booking_data
            df.to_csv(csv_file, index=False)
        except Exception as csv_error:
            print(f"Warning: Could not save to CSV: {csv_error}")
        
        return {
            "success": True,
            "booking_id": booking_id,
            "product_name": product["name"],
            "quantity": quantity,
            "unit_price": f"₹{unit_price}",
            "product_total": f"₹{product_total}",
            "distance_km": distance_km,
            "shipping_cost": f"₹{shipping_cost}",
            "total_price": f"₹{total_price}",
            "delivery_city": delivery_city,
            "delivery_address": address,
            "estimated_delivery": f"{delivery_days}-{delivery_days+1} business days",
            "status": "Order Confirmed"
        }
    except Exception as e:
        return {"success": False, "message": f"Error processing order: {str(e)}"}

# Create tools list for the agent
tools = [show_all_products, get_product_details, get_product_description, find_delivery_city, generate_booking_id, process_order]

def find_agruments(chunk_list: list, fn_name: str) :
    # print(f"\nhidden_file2:\nFound chunks :\n{chunk_list = }\n","==x=="*5)
    
    
    tool_calls_list = list()

    for i, out_chunk in enumerate(chunk_list):
        if 'agent' in out_chunk:
            if not out_chunk['agent']['messages'][0].content:
                tool_calls_list.extend(out_chunk['agent']['messages'][0].additional_kwargs['tool_calls'])
                print(f"{i= }")
            
            elif i == len(chunk_list)-1 and len(tool_calls_list) == 0:
                return False, "FUNCTIONS ARE NOT CALLED"
                
            
            
    print(f"\n{tool_calls_list  =  }\n\n")
    for tool_used in tool_calls_list:
        if tool_used['function']['name'] == fn_name :
            return True, json.loads(tool_used['function']['arguments'])
        
    return False, 'FUNCTIONS ARE CALLED BUT NOT MATCHED'

