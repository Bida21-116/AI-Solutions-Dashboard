import pandas as pd
import random
import faker
from datetime import datetime, timedelta
from ipaddress import IPv4Address

# Initialize Faker
fake = faker.Faker()
random.seed(42)

available_countries = [
    'United Kingdom', 'Germany', 'France', 'Canada', 'India',
    'South Africa', 'Australia', 'Japan', 'Brazil', 'Kenya',
    'United States', 'Netherlands', 'Nigeria', 'China', 'Singapore'
]

product_names = ['AI Virtual Assistant', 'Prototyping Tool', 'HR Automation Suite',
                 'Predictive Maintenance AI', 'Customer Service Bot']
product_categories = ['AI Assistant', 'Prototyping', 'HR Tools', 'Automation', 'Customer Support']
user_interactions = ['Schedule Demo', 'Request Promotional Event', 'Use AI Assistant',
                     'Browse Jobs', 'Request Job Posting']
source_channels = ['Website', 'Email', 'Partner', 'Social Media', 'Direct']
referral_sources = ['Google Ads', 'LinkedIn', 'Newsletter', 'Twitter', 'Facebook']
event_types = ['Webinar', 'Product Launch', 'AI Workshop', 'Networking Event']

device_weights = {'Mobile': 0.5, 'Desktop': 0.35, 'Tablet': 0.15}
browser_weights = {'Chrome': 0.6, 'Firefox': 0.2, 'Safari': 0.15, 'Edge': 0.05}

def generate_random_ip():
    return str(IPv4Address(random.randint(1, 2**32 - 1)))

def generate_data(n=200000):
    data = []
    for _ in range(n):
        timestamp = fake.date_time_between(start_date='-30d', end_date='now')
        weekday = timestamp.weekday()

        ip = generate_random_ip()
        country = random.choices(available_countries, weights=[10,8,8,7,12,5,7,6,6,5,14,6,6,9,4], k=1)[0]
        customer_name = fake.name()
        user_id = random.randint(10000, 99999)  # 5-digit user ID
        product = random.choice(product_names)
        category = product_categories[product_names.index(product)]
        interaction = random.choices(user_interactions, weights=[5,2,7,3,3])[0]
        is_demo = interaction == 'Schedule Demo'
        is_ai_assistant = interaction == 'Use AI Assistant'
        is_job_post = interaction == 'Request Job Posting'

        # Device and browser probabilities
        device_type = random.choices(list(device_weights.keys()), weights=device_weights.values())[0]
        browser = random.choices(list(browser_weights.keys()), weights=browser_weights.values())[0]

        # Request details
        req_type = 'GET'
        resource = f'/{product.replace(" ", "").lower()}.php'
        status = random.choice([200, 200, 304, 500, 404])
        session_duration = int(abs(random.gauss(300, 150))) + 30

        source_channel = random.choices(source_channels, weights=[25, 10, 10, 20, 35])[0]
        referral_source = random.choice(referral_sources)
        product_page_visited = random.choices([True, False], weights=[0.7, 0.3])[0]
        event_type = random.choice(event_types)

        # Conversion logic
        if is_demo or product_page_visited or source_channel == 'Direct':
            conversion_status = random.choices(['Converted', 'Not Converted', 'In Progress'], weights=[0.6, 0.3, 0.1])[0]
        else:
            conversion_status = random.choices(['Converted', 'Not Converted', 'In Progress'], weights=[0.2, 0.6, 0.2])[0]

        # Sales depend on conversion and session duration
        if conversion_status == 'Converted':
            base_sale = random.uniform(300, 10000)
        elif conversion_status == 'In Progress':
            base_sale = random.uniform(50, 500)
        else:
            base_sale = random.uniform(0, 50)

        sales = round(base_sale * (1 + session_duration / 10000), 2)

        data.append([
            timestamp, ip, country, customer_name, user_id, req_type, resource, status,
            product, category, interaction, is_demo, is_ai_assistant, is_job_post,
            session_duration, conversion_status, source_channel,
            referral_source, device_type, browser, product_page_visited,
            event_type, sales
        ])

    return data

columns = [
    'Timestamp', 'IP Address', 'Country', 'Customer Name', 'User ID', 'Request Type',
    'Resource', 'HTTP Status', 'Product Name', 'Product Category',
    'User Interaction', 'Is Demo Request', 'Is AI Assistant Used',
    'Is Job Posted', 'Session Duration(s)', 'Conversion Status',
    'Source Channel', 'Referral Source', 'Device Type', 'Browser',
    'Product Page Visited', 'Event Type', 'Sales(P)'
]

# Generate and save
df = pd.DataFrame(generate_data(200000), columns=columns)
df.to_csv('product_sales_logs(1).csv', index=False)

print("✅CSV dataset generated")