import streamlit as st

def show_statistics(describe):
     col_sorted=['price','availability_365','beds','accommodates','availability_60','review_scores_rating','reviews_per_month','availability_30']
     st.dataframe(describe[col_sorted])
     
     


           
    