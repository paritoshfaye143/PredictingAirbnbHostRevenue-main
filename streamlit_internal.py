import streamlit as st
import sys
base_dir='.'
st.set_page_config(page_title='AirBnB internal')
from pipeline import * 


@st.cache
def get_cities():
    from bs4 import BeautifulSoup
    import requests
    url = "http://insideairbnb.com/get-the-data/"
    req = requests.get(url)
    soup = BeautifulSoup(req.text, "html.parser")
    links_scraped = []
    for link in soup.find_all('a'):
        if link.get('href') is not None:
            links_scraped.append(link.get('href'))
    links_scraped = [x for x in links_scraped if 'csv' in x]
    links_df=Preprocess.parse_urls(links_scraped)
    return links_df.city.unique()

def load_city():  
    with st.form("my_form"):

       city_re = re.compile('DataInterface_(.*)\.obj')
       city_list = [city_re.findall(file)[0] for file in os.listdir(base_dir) if city_re.match(file)]
       cities=[city for city in get_cities() if city  not in city_list]
       city=st.selectbox('Select City :',cities)
       submitted = st.form_submit_button("Build pipeline")
       
       if submitted:
           st.write('[0] Started')
           etl(city)
           st.write('[1] ETL done')
           
           import pickle
           st.write('[2] started modelling')
           modeling(city)
           st.write('[3] revenue model trained')
           st.write('[4] booking rate model trained')

           import pickle
           st.write('[5] Insights')
           insights(city)
           st.write('[6] Insights created')
           combine(city)
           st.write('[7] Done')
def show_metrics():
    import pandas as pd
    metrics=open(f'{base_dir}/metrics.csv','r')
    st.dataframe(pd.read_csv(metrics,names=['city','target','MAE','RMSE','R2']))
    metrics.close()
    
    
page = st.sidebar.radio('Internal', ("Pipeline", "Metrics"),horizontal =True)
if page == "Pipeline":
    load_city()  
elif page == 'Metrics':
    show_metrics()
    
