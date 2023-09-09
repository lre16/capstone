import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import requests
from fake_useragent import UserAgent
import datetime
import base64
import re
import numpy as np
import pandas as pd
import time


tab1, tab2 = st.tabs(["Spinneys", "Carrefour"])

with tab1:
    # Create User-Agent
    ua = UserAgent()

    def get_exchange_rate():
        # Send a request to the homepage
        response = requests.get('https://www.spinneyslebanon.com/default/')
        content = response.text

        # Create a BeautifulSoup object from the page content
        soup = BeautifulSoup(content, 'html.parser')

        # Find all 'a' tags with href='javascript:;'
        a_elements = soup.find_all('a', href='javascript:;')

        # Filter the elements by content
        exchange_rate_element = None
        for element in a_elements:
            if "USD" in element.text and "LBP" in element.text:
                exchange_rate_element = element
                break

        if exchange_rate_element is not None:
            # Extract the exchange rate
            exchange_rate_text = exchange_rate_element.text

            # We can extract the numeric rate with some string processing:
            rate_parts = exchange_rate_text.split('=')
            if len(rate_parts) >= 2:
                numeric_part = rate_parts[1].strip().split(' ')[0].replace(',', '')
                try:
                    return float(numeric_part)
                except ValueError:
                    print(f'Failed to convert exchange rate to float: {numeric_part}')
            else:
                print("Invalid exchange rate format")
        else:
            print("Exchange rate element not found")

        return None
    

    def scrape_products(base_url, desired_products):
        product_names = []
        weights = []
        prices = []
        categories = []

        page_number = 1

        while True:
            url = f'{base_url}?p={page_number}'

            headers = {
                "User-Agent": ua.random
            }

            response = requests.get(url, headers=headers)
            content = response.text

            soup = BeautifulSoup(content, 'html.parser')

            product_elements = soup.find_all('div', {'class': 'product-item-info'})

            if len(product_elements) == 0:
                break

            for element in product_elements:
                product_name_element = element.find('a', {'class': 'product-item-link'})
                product_name = product_name_element.text.strip()

                for product, category in desired_products.items():
                    if product.lower() in product_name.lower():
                        weight_element = element.find('span', {'class': 'prod_weight'})
                        if weight_element:
                            weight_number = weight_element.find('span', {'class': 'weight_number'}).text.strip()
                            weight_unit = weight_element.contents[1]
                            weight = f"{weight_number} {weight_unit}"
                        else:
                            weight = ''

                        price_element = element.find('span', {'class': 'price'})
                        price = price_element.text.strip()

                        product_names.append(product_name)
                        weights.append(weight)
                        prices.append(price)
                        categories.append(category)

            page_number += 1

            data = {'Product Name': product_names, 'Weight': weights, 'Price': prices, 'Category': categories}
            df = pd.DataFrame(data)

        return df

    def fetch_exchange_rate():
        headers = {"User-Agent": ua.random}
        response = requests.get('https://www.spinneyslebanon.com/default/', headers=headers)
        content = response.text
        soup = BeautifulSoup(content, 'html.parser')
        a_elements = soup.find_all('a', href='javascript:;')

        exchange_rate_element = None
        for element in a_elements:
            if "USD" in element.text and "LBP" in element.text:
                exchange_rate_element = element
                break

        if exchange_rate_element is not None:
            exchange_rate_text = exchange_rate_element.text
            try:
                exchange_rate = float(exchange_rate_text.split('=')[1].strip().split(' ')[0])
            except (IndexError, ValueError):
                exchange_rate = None
        else:
            exchange_rate = None

        return exchange_rate


    def combine_and_adjust_dataframes(dfs, exchange_rate):
        df = pd.concat(dfs)
        df.reset_index(drop=True, inplace=True)
        df['Price'] = df['Price'].replace({'[^0-9\.]':''}, regex=True).astype(float)
        df['Exchange Rate'] = exchange_rate
        df['Price in LBP'] = df['Price'] * df['Exchange Rate']

        columns_order = ['Product Name', 'Weight', 'Price', 'Category', 'Exchange Rate', 'Price in LBP']
        df = df[columns_order]

        return df

    def download_csv(dataframe):
        csv = dataframe.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="products.csv">Download CSV</a>'
        return href

    def main():
        st.header('Spinneys Lebanon Scrape Tool')
        st.write('A specialized tool for scraping a selected food items from Spinneys Lebanon.')
        st.warning("In case the scrape did not work, kindly re-check the current availability of the website and re-run the scrape later.")


        if st.button('Start Scraping',key='unique_key_1'):
            with st.spinner('Scraping...'):
            # Define URLs and products
                df1_base_url = 'https://www.spinneyslebanon.com/default/food-cupboard/rice-pasta-pulses.html'
                df1_desired_products = {
                    'Spaghetti': 'Pasta', 'Basmati Rice': 'Basmati Rice', 'Egyptian Rice': 'Egyptian Rice', 
                    'Italian Rice': 'Italian Rice', 'Lentils': 'Lentils', 'White Beans': 'White Beans',
                    'Chickpeas': 'Chickpeas', 'Brown Bulgur': 'Brown Bulgur'
                }
                df2_base_url = 'https://www.spinneyslebanon.com/default/fruits-vegetables.html'
                df2_desired_products ={'Potato': 'Potato', 'Oranges': 'Oranges', 'Cabbage': 'Cabbage', 'Apples': 'Apples',
                    'Carrots': 'Carrots', 'Cucumber': 'Cucumber', 'Tomato': 'Tomato', 'Onion': 'Onion',
                    'Zucchini': 'Zucchini', 'Garlic': 'Garlic', 'Parsley': 'Parsley', 'Banana': 'Banana',
                    'Thyme': 'Thyme', 'Rocca': 'Rocca', 'Spinach': 'Spinach', 'lettuce': 'Lettuce'}
                df3_base_url = 'https://www.spinneyslebanon.com/default/meat-seafood/chicken-poultry.html'
                df3_desired_products = {'Whole Chicken':'Chicken'}
                df4_base_url = 'https://www.spinneyslebanon.com/default/deli-dairy-eggs.html'
                df4_desired_products = {'Laban': 'Yogurt', 'Processed Cheese': 'Canned Cheese', 'Eggs': 'Eggs'}
                df5_base_url = 'https://www.spinneyslebanon.com/default/beverages/milk/powder-milk.html'
                df5_desired_products = {'Powdered Milk':'Milk'}
                df6_base_url = 'https://www.spinneyslebanon.com/default/food-cupboard.html'
                df6_desired_products = {
                    'green peas': 'Canned Green Peas', 
                    'iodized salt': 'Salt', 
                    'fine salt': 'Salt', 
                    'white sugar': 'Sugar',
                    'sardine': 'sardine', 
                    'tahineh': 'tahini', 
                    'mortadella beef': 'Canned Beef',
                    'beef luncheon': 'Canned Beef', 
                    'sunflower oil': 'Oil',
                    'tomato paste' : 'Tomato Paste',
                }
                df7_base_url = 'https://www.spinneyslebanon.com/default/bakery/bread/arabic-bread.html'
                df7_desired_products = {'Pita':'Bread', 'Arabic':'Bread'}
                df8_base_url = 'https://www.spinneyslebanon.com/default/beverages/teas-herbals/green-tea.html'
                df8_desired_products = {'Lipton Tea':'Tea'}

                # Scrape products
                df1_scrape = scrape_products(df1_base_url, df1_desired_products)
                df2_scrape = scrape_products(df2_base_url, df2_desired_products)
                df3_scrape = scrape_products(df3_base_url, df3_desired_products)
                df4_scrape = scrape_products(df4_base_url, df4_desired_products)
                df5_scrape = scrape_products(df5_base_url, df5_desired_products)
                df6_scrape = scrape_products(df6_base_url, df6_desired_products)
                df7_scrape = scrape_products(df7_base_url, df7_desired_products)
                df8_scrape = scrape_products(df8_base_url, df8_desired_products)

        
                dfs = [df1_scrape, df2_scrape,df3_scrape,df4_scrape,df5_scrape,df6_scrape,df7_scrape,df8_scrape]
                df = pd.concat(dfs)
                df.reset_index(drop=True, inplace=True)
                df['Price'] = df['Price'].replace({'[^0-9\.]':''}, regex=True).astype(float)
                exchange_rate = get_exchange_rate()
                df['Exchange Rate'] = exchange_rate
                df['Price in LBP'] = df['Price'] * df['Exchange Rate']

                columns_order = ['Product Name', 'Weight', 'Price', 'Category', 'Exchange Rate', 'Price in LBP']
                df = df[columns_order]
                st.success('Scraping completed!')

            st.dataframe(df)


            # Provide option to download CSV
            st.markdown(download_csv(df), unsafe_allow_html=True)
            
            

    # Function to download dataframe as CSV
    def download_csv(dataframe):
        today = datetime.datetime.today().strftime('%Y-%m-%d')
        filename = f"spinneys_food_basket_scrape_{today}.csv"
        csv = dataframe.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">Download CSV</a>'
        return href


    main()

with tab2:
    
   def get_driver():
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')  # Run Chrome in headless mode
        chrome_options.add_argument('--no-sandbox')  # Bypass OS security model
        chrome_options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems
        chrome_options.add_argument('--disable-gpu')  
        return webdriver.Chrome(options=chrome_options)

    def main():
        ua = UserAgent()
        user_agent = ua.random
        options = Options()
        options.add_argument(f'user-agent={user_agent}')
        driver = webdriver.Chrome(options=options)

    def extract_weight(row):
                # If weight is already defined, return it
                if pd.notna(row['Weight']):
                    return row['Weight']
                else:
                    # Extract weight information using regex
                    match = re.search(r'(\d+(\.\d+)?)(\s*)(GR|KG|G|g|Gr|Kg|ML|ml|Ml|L|l)', row['Product Name'], re.IGNORECASE)

                    # Check if a match is found
                    if match:
                        # If found, return the match
                        return float(match.group(1))
                    else:
                        # If not found, return NaN
                        return np.nan

    def get_exchange_rate():
        # Send a request to the homepage
        response = requests.get('https://www.spinneyslebanon.com/default/')
        content = response.text

        # Create a BeautifulSoup object from the page content
        soup = BeautifulSoup(content, 'html.parser')

        # Find all 'a' tags with href='javascript:;'
        a_elements = soup.find_all('a', href='javascript:;')

        # Filter the elements by content
        exchange_rate_element = None
        for element in a_elements:
            if "USD" in element.text and "LBP" in element.text:
                exchange_rate_element = element
                break

        if exchange_rate_element is not None:
            # Extract the exchange rate
            exchange_rate_text = exchange_rate_element.text

            # We can extract the numeric rate with some string processing:
            rate_parts = exchange_rate_text.split('=')
            if len(rate_parts) >= 2:
                numeric_part = rate_parts[1].strip().split(' ')[0].replace(',', '')
                try:
                    return float(numeric_part)
                except ValueError:
                    print(f'Failed to convert exchange rate to float: {numeric_part}')
            else:
                print("Invalid exchange rate format")
        else:
            print("Exchange rate element not found")

        return None

    def scroll_page(driver):
        # Get scroll height
        last_height = driver.execute_script("return document.body.scrollHeight")

        while True:
            # Scroll down to the bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            # Wait for new page segment to load
            time.sleep(2)

            # Calculate new scroll height and compare with last scroll height
            new_height = driver.execute_script("return document.body.scrollHeight")

            if new_height == last_height:
                # If heights are the same it will exit the function
                break

            last_height = new_height

    def scrape(driver, url, desired_products):
        data = {'Product Name': [], 'Category': [], 'Weight': [], 'Price': []}
        driver.get(url)

        # Scroll the page before parsing the content
        scroll_page(driver)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        product_items = soup.find_all("div", class_="css-yqd9tx")

        for item in product_items:
            product_name = item.find("a", {"data-testid": "product_name"}).text.strip()

            for word in desired_products:
                if any(all(product_form_word.lower() in product_name.lower().split() for product_form_word in product_form.lower().split()) for product_form in desired_products[word]):
                    weight = item.find("div", class_="css-149zse0").text.strip().replace(" - Approx", "")
                    price = item.find("div", class_="css-14zpref").text.strip().replace(',', '')

                    data['Product Name'].append(product_name)
                    data['Category'].append(word)
                    data['Weight'].append(weight)
                    data['Price'].append(price)

        return pd.DataFrame(data)

    def make_download_link(df):
            csv = df.to_csv(index=False)
            # Get the current date
            today = datetime.datetime.today().strftime('%Y-%m-%d')

            # Create the filename
            csv_file_name = f"carrefour_food_basket_scrape_{today}.csv"
            b64 = base64.b64encode(csv.encode()).decode()

            # Adjust the filename in the href link
            href = f'<a href="data:file/csv;base64,{b64}" download="{csv_file_name}">Download CSV File</a>'
            return href


    def main():
    # Setup selenium webdriver in headless mode
        ua = UserAgent()
        user_agent = ua.random
        options = Options()
        options.add_argument('--headless')  # Run Chrome in headless mode
        options.add_argument(f'user-agent={user_agent}')
        driver = webdriver.Chrome(options=options)
        

        st.header('Carrefour Lebanon website Scrape Tool')
        st.write('A specialized tool for scraping a selected food items from Carrefour Lebanon.')
        st.warning("In case the scrape did not work, kindly re-check the current availability of the website and re-run the scrape later.")

        urls = {
            'fruits_vegetables': [
                "https://www.carrefourlebanon.com/maflbn/en/c/FLEB1660100",  # Fruits
                "https://www.carrefourlebanon.com/maflbn/en/c/FLEB1660500",  # Vegetables
            ],
            'grains': [
                "https://www.carrefourlebanon.com/maflbn/en/c/FLEB1701220?currentPage=2&filter=&pageSize=60&sortBy=relevance",  # Pasta
                "https://www.carrefourlebanon.com/maflbn/en/c/FLEB1701230?currentPage=1&filter=&pageSize=60&sortBy=relevance", # Brown bulgur, white beans, lentils
                "https://www.carrefourlebanon.com/maflbn/en/c/FLEB1701240",  # Rice
            ],
            'processed_food': [
                "https://www.carrefourlebanon.com/maflbn/en/v4/search?keyword=chickpeas",  # Chickpeas
                "https://www.carrefourlebanon.com/maflbn/en/c/FLEB1630200?currentPage=1&filter=&pageSize=60&sortBy=relevance",  # Processed cheese
                "https://www.carrefourlebanon.com/maflbn/en/c/FLEB1714600",  # Powdered Milk
                "https://www.carrefourlebanon.com/maflbn/en/c/FLEB1714500",  # Canned beef
            ],
            'grocery': [
                "https://www.carrefourlebanon.com/maflbn/en/c/FLEB1760400",  # Sunflower Oil
                "https://www.carrefourlebanon.com/maflbn/en/c/FLEB1701350",  # Sugar
                "https://www.carrefourlebanon.com/maflbn/en/c/FLEB1760100",  # Tomato Paste
                "https://www.carrefourlebanon.com/maflbn/en/c/FLEB1714100",  # Green peas
            ],
            'other': [
                "https://www.carrefourlebanon.com/maflbn/en/c/FLEB1200702",  # Tea
                "https://www.carrefourlebanon.com/maflbn/en/c/FLEB1714900",  # Sardine
                "https://www.carrefourlebanon.com/maflbn/en/c/FLEB1630400",  # Eggs
                "https://www.carrefourlebanon.com/maflbn/en/c/FLEB1670300",  # Chicken
            ],
            'additional': [
                "https://www.carrefourlebanon.com/maflbn/en/v4/search?keyword=tahini",  # Tahini
                "https://www.carrefourlebanon.com/maflbn/en/c/FLEB1630500",  # Laban
                "https://www.carrefourlebanon.com/maflbn/en/c/FLEB1760000",  # Salt
            ],
        }

        desired_products = {
            'fruits_vegetables': {
                'Rocca': ['Rocca'],
                'Lettuce': ['lettuce'],
                'Potato': ['Potato', 'Potatoes'],
                'Orange': ['Orange', 'Oranges'],
                'Cabbage': ['Cabbage', 'Cabbages'],
                'Apple': ['Apple', 'Apples'],
                'Carrot': ['Carrot'],
                'Cucumber': ['Cucumber', 'Cucumbers'],
                'Tomato': ['Tomato', 'Tomatoes'],
                'Onion': ['Onion', 'Onions'],
                'Zucchini': ['Zucchini', 'Zucchinis'],
                'Garlic': ['Garlic', 'Garlics']
            },
            'grains': {
                'Pasta': ['Spaghetti', 'Penne'],
                'White beans': ['White kidney beans'],
                'Brown bulgur': ['brown bulgur'],
                'Lentils': ['Lentils'],
                'Rice': ['Egyptian rice']
            },
            'processed_food': {
                'Chickpeas': ['Chickpeas'],
                'Canned cheese': ['Processed cheese'],
                'Powdered Milk': ['Milk Powder', 'powdered milk'],
                'Canned beef': ['Corned beef']
            },
            'grocery': {
                'Sunflower oil': ['sunflower oil'],
                'Sugar': ['sugar'],
                'Tomato paste': ['Tomato paste'],
                'Green peas': ['green peas']
            },
            'other': {
                'Tea': ['tea'],
                'Sardine': ['sardine'],
                'Eggs': ['eggs'],
                'Chicken': ['chicken']
            },
            'additional': {
                'Tahini': ['Tahina'],
                'Laban': ['Laban'],
                'Salt': ['fine salt', 'iodized salt', 'Fine sea salt']
            },
        }

        all_dataframes = []  # Initialize an empty list to store the DataFrames for each category

        # Scrape all categories when the "Start Scraping" button is clicked
        # Scrape all categories when the "Start Scraping" button is clicked
        if st.button('Start Scraping'):
            for category in urls.keys():
                with st.spinner(f'Scraping {category}...'):
                    dataframes = []  # Define an empty list before scraping each category
                    for url in urls[category]:
                        df = scrape(driver, url, desired_products[category])
                        dataframes.append(df)
                    if dataframes:
                        combined_df = pd.concat(dataframes)
                        combined_df['Weight'] = combined_df.apply(extract_weight, axis=1)  # Apply function after concatenation
                        all_dataframes.append(combined_df)
                    st.success(f'Scraping {category} completed.')

            driver.quit()

        if all_dataframes:  # Save the combined DataFrame if there is any data
        

            combined_df = pd.concat(all_dataframes)
            today = datetime.date.today()
            combined_df['Date'] = today
            exchange_rate = get_exchange_rate()
            combined_df['Exchange Rate'] = exchange_rate
            combined_df['Price'] = pd.to_numeric(combined_df['Price'], errors='coerce')
            combined_df['Price in USD'] = combined_df['Price'] / combined_df['Exchange Rate']
            combined_df.rename(columns={'Price': 'Price in LBP'}, inplace=True)
            columns_order = ['Product Name', 'Weight', 'Category', 'Exchange Rate', 'Price in LBP', 'Price in USD', 'Date']
            combined_df = combined_df[columns_order]

            # Get the current date
            today = today.strftime('%Y-%m-%d')

            # Create the filename
            csv_file_name = f"carrefour_food_basket_scrape_{today}.csv"

            combined_df.to_csv(csv_file_name, index=False)

            st.success(f'All data scraped from all categories has been saved to {csv_file_name}.')


        # Display the combined DataFrame and the download link
        if all_dataframes:
            st.write(combined_df)
            st.markdown(make_download_link(combined_df), unsafe_allow_html=True)
            # Add the disclaimer message right after:
        
            
    
    if __name__ == "__main__":
        main()



