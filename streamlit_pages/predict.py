import streamlit as st
import numpy as np


def show_predict_page(model_revenue,model_booking_rate,describe):
    
    def get_min_value(col_name):
        if col_name=='price':
            return 10
        return round(describe.loc['min',col_name])
    def get_mean_value(col_name):
        return round(describe.loc['50%',col_name])
    def get_max_value(col_name):
        return round(((describe.loc['75%',col_name]-describe.loc['25%',col_name])*1.5)+describe.loc['mean',col_name])
    col_sorted=['price','availability_365','beds','accommodates','availability_60','review_scores_rating','reviews_per_month','availability_30']  
    st.title("""Revenue and Booking Rate Prediction""")

    
    st.sidebar.subheader(' ')
    inputs=[]
    for col in col_sorted:
        inputs.append(st.sidebar.slider(col,get_min_value(col),get_max_value(col),get_mean_value(col)))
    
    
    safe_html="""  
      <div style="background-color:#EEF1FF;padding:10px >
        <h2 style="text-align: center;color:black;"> {} is in the top {}% population</h2>
        </div>
    """
    danger_html="""  
      <div style="background-color:#F08080;padding:10px >
        <h2 style="'color':black ;'text-align' : center;"> {} is in the bottom {}% population</h2>
        </div>
    """
    medium_html="""  
      <div style="background-color:#F1E36B;padding:10px >
        <h2 style="'color':black ;'text-align' : center;"> {} is in the top {}% population</h2>
        </div>
    """
    


    input=np.array([inputs]).astype(np.float64)

    output=model_revenue.predict(input)
    st.success(f'Predicted Revenue is ${round(float(output),2)} ')

    st.text('                                        ') 
    output2=model_booking_rate.predict(input)
    st.success(f'Predicted Booking rate is {round(float(output2),2)}%')
    if output2 < describe.loc['25%','booking_rate']:
        st.markdown(danger_html.format('booking rate','25'),unsafe_allow_html=True)
    elif output2 < describe.loc['75%','booking_rate']:
        st.markdown(medium_html.format('booking rate','75'),unsafe_allow_html=True)
    else:
        st.markdown(safe_html.format('booking rate','25'),unsafe_allow_html=True)
    st.text('                                        ')
    st.text('                                        ')
    st.write("-" * 34)
    
    