import streamlit as st
import time
from streamlit_pages.predict import show_predict_page
from streamlit_pages.explore_page import show_explore_page
from streamlit_pages.stats import show_statistics
import os
import pickle



from pipeline import *
import re


base_dir='.'

st.set_page_config(page_title='AirBnB')

city_re = re.compile('DataInterface_(.*)\.obj')
city_list = [city_re.findall(file)[0] for file in os.listdir(base_dir) if city_re.match(file)]

with st.spinner('Loading...'):
    time.sleep(0.1)


city=st.sidebar.selectbox('Select City :',city_list)

@st.cache
def get_data_interface(city):
    return pickle.load(open(f'{base_dir}/DataInterface_{city}.obj','rb'))

data_interface=get_data_interface(city)


def get_revenue_model():
    return data_interface.get_model('revenue')

def get_booking_rate_model():
    return data_interface.get_model('booking_rate')


def get_insight():
    return data_interface.get_insight_engine()


page = st.sidebar.radio('Explore Data Or Predict', ("Predict", "Explore Data","Statistics"),horizontal =True)

if page == "Predict":
    show_predict_page( get_revenue_model(),get_booking_rate_model(),get_insight().describe)
    
elif page == 'Statistics':
    show_statistics(get_insight().describe)  
else:
    show_explore_page(get_insight().insights)


    



    



