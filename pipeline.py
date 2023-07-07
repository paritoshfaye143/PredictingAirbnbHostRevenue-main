import os
import warnings
warnings.filterwarnings("ignore")
import pandas as pd
import re
log={}
class Preprocess:
    def __init__(self, name):
        self.city_name = name

    @staticmethod
    def get_processed_dfs(calendar_df, listings_df):
        listings_df['price'] = listings_df['price'].astype(str).map(lambda x: x.lstrip("$").replace(",", "")).astype(float)
        calendar_df['price'] = calendar_df['price'].astype(str).map(lambda x: x.lstrip("$").replace(",", "")).astype(float)
        calendar_df['available'] = calendar_df['available'].map({'t':1, 'f':0})
        calendar_df['revenue'] = calendar_df['price']*calendar_df['available']
        calendar_df = calendar_df.fillna(0)
        overview = calendar_df.groupby('listing_id').mean()
        overview['daily_revenue'] = overview['revenue']
        overview['booking_rate'] = overview['available']*100
        calendar_booked = calendar_df[calendar_df['price']!=0]
        calendar_booked = calendar_booked.groupby('listing_id').agg({'price':['mean','std']}).reset_index()
        calendar_booked.columns=['listing_id','price_avg','price_std']
        pricing_strategies = ['price', 'accommodates']

        for col in pricing_strategies:
                  listings_df[col] = listings_df[col].astype(str).map(lambda x: x.lstrip("$").replace(",", "")).astype(float)
        listings_df = listings_df.drop('price', axis=1)
        overview = overview[['available', 'price', 'revenue',
                  'daily_revenue', 'booking_rate']]
        listings_df = pd.merge(listings_df, overview, how='left', left_on='id', right_on='listing_id')
        listings_df = pd.merge(listings_df, calendar_booked, how='left', left_on='id', right_on='listing_id')
        listings_df['price_per_person'] = listings_df['price'] / listings_df['accommodates']
        listings_df = listings_df.drop(['listing_id'], axis=1)
        listings_df['accom_per_bed'] = listings_df['accommodates']/listings_df['beds']
        listings_df['price_surge_percent'] = (listings_df['price_avg']/listings_df['price']-1)*100
        #To check abrupt changes in price during peak season
        listings_df['price_std_percent'] = listings_df['price_std']/listings_df['price']*100
        columns=['host_location','host_response_time','host_response_rate','host_acceptance_rate','host_is_superhost','host_neighbourhood','host_total_listings_count','host_verifications',
        'host_identity_verified','neighbourhood','property_type','room_type','bedrooms','minimum_nights','maximum_nights','has_availability','availability_30','number_of_reviews','number_of_reviews_ltm',
        'number_of_reviews_l30d','review_scores_rating','review_scores_accuracy','review_scores_cleanliness','review_scores_checkin','review_scores_communication','review_scores_location','review_scores_value',
        'instant_bookable','price','price_avg','price_std','beds','accommodates','reviews_per_month','availability_60','availability_90','availability_365','revenue','booking_rate','bathrooms_text','price_per_person',
        'accom_per_bed','price_surge_percent','price_std_percent']
        cleaned_df=listings_df[columns]
        cleaned_df['host_response_rate'] = cleaned_df['host_response_rate'].str.replace('%','').astype('float64')
        cleaned_df['host_acceptance_rate'] = cleaned_df['host_acceptance_rate'].str.replace('%','').astype('float64')
        mylist=cleaned_df[cleaned_df.columns[cleaned_df.isnull().any()]].isnull().columns
        dtype_num=cleaned_df[mylist].select_dtypes(include=['float64','int64']).columns
        for col in dtype_num:
          cleaned_df[col]=cleaned_df[col].fillna(cleaned_df[col].mean())
        cleaned_df['host_location']=cleaned_df['host_location'].fillna('host location not available')
        cleaned_df['host_response_time']=cleaned_df['host_response_time'].fillna('response not available')
        cleaned_df['host_is_superhost']=cleaned_df['host_is_superhost'].fillna(cleaned_df['host_is_superhost'].mode()[0])
        cleaned_df['host_neighbourhood']=cleaned_df['host_neighbourhood'].fillna('host neighbourhood not available')
        cleaned_df['neighbourhood']=cleaned_df['neighbourhood'].fillna('neighbourhood not available')
        cleaned_df['bathrooms_text']=cleaned_df['bathrooms_text'].fillna(cleaned_df['bathrooms_text'].mode()[0]) 
        return calendar_df,cleaned_df

    @staticmethod
    def parse_urls(links):
        return pd.DataFrame(
            {"link": links, 'country': [x.split('/')[3] for x in links], 'state': [x.split('/')[4] for x in links],
             'city': [x.split('/')[5] for x in links], 'type': [re.search(r'(\w*)\.csv', x)[1] for x in links]})

class City:
    def __init__(self, name, urls):
        parsed_urls = Preprocess.parse_urls(urls)
        self.name = name
        self.listings_url = parsed_urls.loc[(parsed_urls['type'] == 'listings') & (parsed_urls['city'] == name)].iloc[
            0].link
        self.calendar_url = parsed_urls.loc[(parsed_urls['type'] == 'calendar') & (parsed_urls['city'] == name)].iloc[
            0].link

class DataInterface:
    def __init__(self, name, storage_type='local', access_mode='default', location=None, get_data=None):
        self.city = name
        self.storage_type = storage_type
        self.location = location
        self.access_mode = access_mode
        if get_data is not None:
            self.get_data = get_data

    def get_data(self):
        if self.storage_type == 'local':
            self.location = self.location if self.location is not None else f'./Data/{self.city}'
            return  'listings', pd.read_csv(f'{self.location}/listings.csv') 
        elif self.storage_type == 'hdfs':
            import os
            import sys

            os.environ["SPARK_HOME"] = "/home/talentum/spark"
            os.environ["PYLIB"] = os.environ["SPARK_HOME"] + "/python/lib"
            os.environ["PYSPARK_PYTHON"] = "/usr/bin/python3.6" 
            os.environ["PYSPARK_DRIVER_PYTHON"] = "/usr/bin/python3"
            sys.path.insert(0, os.environ["PYLIB"] +"/py4j-0.10.7-src.zip")
            sys.path.insert(0, os.environ["PYLIB"] +"/pyspark.zip")
            os.environ['PYSPARK_SUBMIT_ARGS'] = '--packages com.databricks:spark-xml_2.11:0.6.0,org.apache.spark:spark-avro_2.11:2.4.3 pyspark-shell'

            from pyspark.sql import SparkSession
            spark = SparkSession.builder.appName("Spark AirBnb Data storage").enableHiveSupport().getOrCreate()
            sc = spark.sparkContext

            a=spark.read.parquet(f'/Data/{self.city}')
            pandasDF = a.toPandas()
            print(pandasDF.head())
            return  'listings',pandasDF
        
    

    def get_insight_engine(self):
        import pickle
        if self.storage_type == 'local':
            self.location = self.location if self.location is not None else f'./Data/{self.city}'
            return pickle.load(open(f'{self.location}/InsightEngine.obj', 'rb'))
        else:
            self.location = self.location if self.location is not None else f'./Data/{self.city}'
            return pickle.load(open(f'{self.location}/InsightEngine.obj', 'rb'))

    def save_insight_engine(self,obj):
        import pickle
        if self.storage_type == 'local':
            self.location = self.location if self.location is not None else f'./Data/{self.city}'
            return pickle.dump(obj,open(f'{self.location}/InsightEngine.obj', 'wb'))
        else:
            self.location = self.location if self.location is not None else f'./Data/{self.city}'
            return pickle.dump(obj,open(f'{self.location}/InsightEngine.obj', 'wb'))


    def get_model(self,target):
        """return revenue and booking rate model"""
        import pickle
        if self.storage_type == 'local':
            self.location = self.location if self.location is not None else f'./Data/{self.city}'
            return pickle.load(open(f'{self.location}/{target}.model', 'rb'))
        else:
            self.location = self.location if self.location is not None else f'./Data/{self.city}'
            return pickle.load(open(f'{self.location}/{target}.model', 'rb'))

    def save_model(self,estimator,target):
        import pickle
        if self.storage_type == 'local':
            self.location = self.location if self.location is not None else f'./Data/{self.city}'
            return pickle.dump(estimator,open(f'{self.location}/{target}.model', 'wb'))
        else:
            self.location = self.location if self.location is not None else f'./Data/{self.city}'
            return pickle.dump(estimator,open(f'{self.location}/{target}.model', 'wb'))
        
    def save_metrics(self,target,metrics):
        if self.storage_type == 'local':
            file=open('metrics.csv','a')
            file.write('\n'+self.city+','+target+','+','.join([str(n) for n in metrics.values()]))
            file.close()
        else:
            file=open('metrics.csv','a')
            file.write('\n'+self.city+','+target+','+','.join([str(n) for n in metrics.values()]))
            file.close()
        
class ETL:
    def __init__(self, city: City, storage_type='local', storage_location=None):
        self.city = city
        self.storage_type = storage_type
        self.storage_location = storage_location
        self.calendar_df = None
        self.listings_df = None
        from time import time
        self.time=time

    def extract(self):  
        self.listings_df = pd.read_csv(self.city.listings_url)
        self.calendar_df = pd.read_csv(self.city.calendar_url)
        log[self.time()]='extraction completed....'
        print('extraction completed....')

    def transform(self):
        self.calender_df,self.listings_df = Preprocess.get_processed_dfs(calendar_df=self.calendar_df, listings_df=self.listings_df)
        log[self.time()]='transformation completed....'
        print('transformation completed....')
        
    def load(self):
        import os
        import sys
        if self.storage_type == 'local':
            self.storage_location = self.storage_location if self.storage_location is not None else f'./Data/{self.city.name}'
            os.makedirs(self.storage_location, exist_ok=True)
            #self.calendar_df.to_csv(f'{self.storage_location}/calendar.csv')
            self.listings_df.to_csv(f'{self.storage_location}/listings.csv')
            log[self.time()]='done loading....'
            print('done loading....')
        
            
    def export_data_interface(self, tofile=False, path='.'):
        dif = DataInterface(self.city.name, storage_type=self.storage_type, location=self.storage_location)
        if tofile:
            import pickle
            pickle.dump(dif, open(f'{path}/DataInterface_{self.city.name}.obj', 'wb'))
        else:
            return dif

class Model:
    def __init__(self,data_interface,target:str,estimator=None):
        self.data_interface=data_interface
        self.estimator=estimator
        self.X_test=None
        self.y_test=None
        self.target=target
        
        
    def train(self):
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler
        from sklearn.model_selection import KFold,GridSearchCV
        from xgboost import XGBRegressor
        import numpy as np
        import pandas as pd
        from sklearn.metrics import r2_score
        from sklearn.pipeline import Pipeline



        def get_top5_host_locations(cleaned_df):
            top_5 = [x for x in cleaned_df.host_location.value_counts().sort_values(ascending=False).head(5).index]
            for label in top_5:
                  cleaned_df[label] = np.where(cleaned_df['host_location']==label,1,0)
            cleaned_df[['host_location']+top_5]
            cleaned_df.drop('host_location',axis=1,inplace=True)
            
        def get_top_10_host_neighbourhoods(cleaned_df):
            top_10 = [x for x in cleaned_df.host_neighbourhood.value_counts().sort_values(ascending=False).head(10).index]
            for label in top_10:
                  cleaned_df[label] = np.where(cleaned_df['host_neighbourhood']==label,1,0)
            cleaned_df[['host_neighbourhood']+top_10]
            cleaned_df.drop('host_neighbourhood',axis=1,inplace=True)
            
        def get_top_5_property_types(cleaned_df):
            top_5 = [x for x in cleaned_df.property_type.value_counts().sort_values(ascending=False).head(5).index]
            for label in top_5:
                  cleaned_df[label] = np.where(cleaned_df['property_type']==label,1,0)
            cleaned_df[['property_type']+top_5]
            cleaned_df.drop('property_type',axis=1,inplace=True)

        def get_top_7_bathrooms_texts(cleaned_df):    
            top_7 = [x for x in cleaned_df.bathrooms_text.value_counts().sort_values(ascending=False).head(7).index]
            for label in top_7:
                  cleaned_df[label] = np.where(cleaned_df['bathrooms_text']==label,1,0)
            cleaned_df[['bathrooms_text']+top_7]
            cleaned_df.drop('bathrooms_text',axis=1,inplace=True)
            
        def get_top_5_neighbourhoods(cleaned_df):    
            top_5 = [x for x in cleaned_df.neighbourhood.value_counts().sort_values(ascending=False).head(5).index]
            for label in top_5:
                  cleaned_df[label] = np.where(cleaned_df['neighbourhood']==label,1,0)
            cleaned_df[['neighbourhood']+top_5]
            cleaned_df.drop('neighbourhood',axis=1,inplace=True)

        def get_dummies(cleaned_df):
            return pd.get_dummies(cleaned_df,drop_first=True)

        def  get_features(cleaned_df):
            get_top5_host_locations(cleaned_df)
            get_top_10_host_neighbourhoods(cleaned_df)
            get_top_5_property_types(cleaned_df)
            get_top_7_bathrooms_texts(cleaned_df)
            get_top_5_neighbourhoods(cleaned_df)
            
            
            dummy_airbnb=get_dummies(cleaned_df)
            
            X= dummy_airbnb.drop(['revenue','booking_rate'],axis=1)
            y= dummy_airbnb[self.target]
            
            col_sorted=['price','availability_365','beds','accommodates','availability_60','review_scores_rating','reviews_per_month','availability_30']
            return (col_sorted,X,y)


        def get_model(cleaned_df):
            selected_features,X,y = get_features(cleaned_df)
            print('#################################################################################################################################################')
            print('Selected features : ',selected_features)
            print('#################################################################################################################################################')
            X = X[selected_features]
            
            
            X_train,X_test,y_train,y_test=train_test_split(X,y,test_size=0.3,random_state=2022)
            
            scaler=StandardScaler()
            scaler.fit(X_train)
            self.scaler=scaler
            self.X_test=scaler.transform(X_test)
            self.y_test=y_test
            
            model_xgb=XGBRegressor(random_state=2022)
            pipe_xgb=Pipeline([('scaler',scaler),('xgb',model_xgb)])
            kfold = KFold(n_splits=5,shuffle=True,random_state=2022)
            params={'xgb__max_depth':[2,3,4,5,6],'xgb__n_estimators':[50,100],'xgb__learning_rate':[0.01,0.3,0.05,0.5,0.7]}
            gcv_xgb=GridSearchCV(pipe_xgb,scoring='r2',param_grid=params,cv=kfold)
            gcv_xgb.fit(X_train,y_train)
           
            print('For train')
            print('Best estimator : ',gcv_xgb.best_estimator_)
            print('Best score : ',gcv_xgb.best_score_)
            print('Best score : ',gcv_xgb.best_params_)
            print('#################################################################################################################################################')

            y_pred = gcv_xgb.predict(X_test)
            from sklearn.metrics import mean_absolute_error,mean_squared_error
            self.metrics= {'mean_absolute_error':mean_absolute_error(y_test,y_pred),'Root_mean_squared_error':mean_squared_error(y_test,y_pred,squared=False),'R2 Score':r2_score(y_test,y_pred)}
            print('For test dataset: ')
            print(self.metrics)
            print('#################################################################################################################################################')
            
            return gcv_xgb.best_estimator_
        self.estimator=get_model(self.data_interface.get_data()[1])
            
    def save(self):
        self.data_interface.save_model(self.estimator,self.target)
        #return self.estimator
   
    
    def save_metrics(self):
        self.data_interface.save_metrics(self.target,self.metrics)
        
    def get_scaled(self,X_in):
        return self.scalar.transform(X_in)

class Listing:
    def __init__(self, kwargs):
        self.price = kwargs['price']
        self.availability_365 = kwargs['availability_365']
        self.beds = kwargs['beds']
        self.accommodates = kwargs['accommodates']
        self.availability_60 = kwargs['availability_60']
        self.review_scores_rating = kwargs['review_scores_rating']
        self.reviews_per_month = kwargs['reviews_per_month']
        self.availability_30 = kwargs['availability_30']
        
        

    def get_processed(self):
        import numpy as np
        return np.array([[self.price,self.availability_365,self.beds,self.accommodates,self.availability_60,self.review_scores_rating,self.reviews_per_month,self.availability_30]]).astype(np.float64)


from matplotlib.figure import Figure


class Insight:
    def __init__(self, plot: Figure, title=None, text=None):
        self.title = title
        self.plot = plot
        self.text = text

class InsightEngine:
    def __init__(self, datainterface, insights):
        self.datainterface = datainterface
        self.insights = insights
        self.describe = datainterface.get_data()[1].describe()
        
        
    def load_model(self):
        self.revenue_model, self.booking_model = self.datainterface.get_model(target='revenue'), self.datainterface.get_model(target='booking_rate')
        

    def get_insights(self):
        return self.insights

    def get_revenue(self, listing: Listing):
        return self.revenue_model.predict(listing.get_processed())

    def get_booking_rate(self, listing: Listing):
        return self.booking_model.predict(listing.get_processed())
    
    def export(self):
        self.datainterface.save_insight_engine(self)

def create_insights(data_interface):
    from matplotlib import pyplot as plt
    insights=[]
    
    # code for first insight 1
    import pickle
    df=data_interface.get_data()[1]
    df_grp = df.groupby("property_type").mean()['revenue'].sort_values(ascending=False).iloc[:5]
    fig1 = plt.figure()
    plt.bar(df_grp.index, df_grp, figure=fig1)
    plt.ylabel('average revenue')
    plt.xlabel('property_type')
    plt.xticks(rotation=90)
    plt.title('Top 5 property types by revenue')

    insight1 = Insight(plot=fig1, title='Top 5 property types by revenue')
    insights.append(insight1)
    # code for first insight 2
    fig2 = plt.figure()
    df_grp = df.groupby('host_identity_verified').mean()['revenue']
    plt.title('Effect of host identity verification on revenue')
    plt.bar(df_grp.index, df_grp, figure=fig2)
    plt.xlabel('host_identity_verified(True,False)')
    plt.ylabel('average Revenue')

    def get_text2():
        if df_grp.loc['f'] > df_grp.loc['t']:
            return 'Verifying your identity might not increase revenue.'
        else:
            return 'Verifying your identity might increase revenue.'

    text2 = get_text2()
    insight2 = Insight(plot=fig2, title='Effect of host identity verification on booking rate and revenue', text=text2)
    insights.append(insight2)
    
    #code for first insight 3
    df_grp = df.groupby('neighbourhood').mean()['revenue'].sort_values(ascending=False).iloc[:5]
    fig3= plt.figure()
    plt.bar(df_grp.index, df_grp, figure=fig3)
    plt.xlabel('neighbourhood')
    plt.ylabel('average revenue')
    plt.xticks(rotation=90)
    plt.title('Top 5 neighborhoods by revenue')
    insight3 = Insight(plot=fig3, title='What are the top 5 neighborhoods/areas to invest in based on average revenue?')
    insights.append(insight3)
    
    #code for insight 4
    df_grp = df.groupby('neighbourhood').mean()['booking_rate'].sort_values(ascending=False).iloc[:5]
    fig4= plt.figure()
    plt.bar(df_grp.index, df_grp, figure=fig4)
    plt.xlabel('neighbourhood')
    plt.ylabel('average booking rate(%)')
    plt.xticks(rotation=90)
    plt.title('Top 5 neighborhoods by booking rate')
    insight4 = Insight(plot=fig4, title='What are the top 5 neighborhoods/areas to invest in based on booking rate?')
    insights.append(insight4)
    
    #code for insight 5
    import numpy as np
    df_grp = df.groupby('accommodates').mean()[['booking_rate','revenue']]
    barWidth = 0.35
    r1 = np.arange(len(df_grp.index))
    r2 = [x + barWidth for x in r1]
    fig5, ax = plt.subplots()
    ax.bar(r1,df_grp['booking_rate'], width=barWidth, label='booking_rate' ,figure=fig5)
    ax.bar(r2,df_grp['revenue'], width=barWidth, label='revenue', figure=fig5)
    plt.xticks(r2,df_grp.index,fontsize=9)
    plt.xlabel('accommodates')
    plt.ylabel('average booking rate(%)/revenue')
    plt.title('Effect of accommodations on booking rate/revenue')
    insight5 = Insight(plot=fig5, title='How does maximum number of people per listing affect revenue/booking rate?')
    insights.append(insight5)
    
    #code for insight 6
    df_grp = df.groupby('property_type').mean()['booking_rate'].sort_values(ascending=False).iloc[:5]
    fig6, ax = plt.subplots()
    plt.bar(df_grp.index, df_grp, figure=fig6)
    plt.xlabel('property_type')
    plt.ylabel('average booking rate(%)')
    plt.xticks(rotation=90)
    plt.title('Top 5 neighborhoods by booking rate')
    insight6 = Insight(plot=fig6, title='Top 5 property types with the highest booking rate?')
    insights.append(insight6)
    
    #code for insight 7
    fig7= plt.figure()
    df_grp = df.groupby('host_is_superhost').mean()['booking_rate']
    plt.bar(df_grp.index, df_grp, figure=fig7)
    plt.xlabel('host_is_superhost',fontsize=10)
    plt.ylabel('average booking_rate',fontsize=10)
    plt.xticks(rotation=90)
    plt.title('effect of superhost on booking_rate')
    insight7 = Insight(plot=fig7, title=' Does being a superhost affect booking rate?')
    insights.append(insight7)
    
    #code for insight 8
    fig8 = plt.figure()
    df_grp = df.groupby('host_location').mean()['price_avg'].sort_values(ascending=False).iloc[:5]
    plt.bar(df_grp.index, df_grp, figure=fig8)
    plt.xlabel('host_location')
    plt.ylabel('average price')
    plt.xticks(rotation=90)
    plt.title('Average Price per Host location',fontsize=10,y=1.0,pad=-20)
    
    insight8 = Insight(plot=fig8, title=' What is the Average Price per Host Location?')
    insights.append(insight8)
    
    
    #code for insight 9
    import numpy as np
    df_grp = df.groupby('room_type').mean()[['booking_rate','revenue']]
    barWidth = 0.35
    r1 = np.arange(len(df_grp.index))
    r2 = [x + barWidth for x in r1]
    fig9, ax = plt.subplots()
    ax.bar(r1,df_grp['booking_rate'], width=barWidth, label='booking_rate' ,figure=fig9)
    ax.bar(r2,df_grp['revenue'], width=barWidth, label='revenue', figure=fig9)
    plt.xticks(r2,df_grp.index)
    plt.xlabel('room_type')
    plt.ylabel('average revenue/ booking rate')
    plt.legend(["booking_rate","revenue"])
    plt.title('effect of room_type on revenue')
    insight9 = Insight(plot=fig9, title=' How room type affect booking rate/average revenue?')
    insights.append(insight9)
    

    #code for insight 10
    fig10= plt.figure()
    
    plt.scatter(df['review_scores_rating'],df['revenue'], figure=fig10)
    plt.xlabel('review_scores_rating')
    plt.ylabel('revenue')
    plt.title('review_scores_rating vs revenue')
    insight10 = Insight(plot=fig10, title=' How review ratings affect revenue and booking rate?')


    insights.append(insight10)

    
    #code for insight 11
    import seaborn as sns
    fig11, ax = plt.subplots()
    sns.countplot(x=df["host_response_time"],figure=fig11 )
    ax.bar_label(ax.containers[-1], fmt='\n%.2f', label_type='edge')
    plt.xticks(rotation=60,fontsize=10)
    plt.title('Host Response Time')
    ax.set(ylabel='count')
    insight11 = Insight(plot=fig11, title=' Host Response Time')
    insights.append(insight11)
    
    
#     #code for insight 12
    fig12 = plt.figure()
    sns.histplot(data=df, x="host_response_rate",bins=10,kde=True,figure=fig12)
    plt.xlim(0,df['host_response_rate'].max()+10 )
    plt.title('Response rate distribution',fontsize=10)
    insight12 = Insight(plot=fig12, title='  Host response rate')
    insights.append(insight12)

    return insights
def etl(city_name):
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
    city = City(city_name, links_scraped)
    etl = ETL(city)
    etl.extract()
    etl.transform()
    etl.load()
    etl.export_data_interface(tofile=True)


def modeling(city_name):
    import pickle
    data_interface_file=open(f'DataInterface_{city_name}.obj','rb')
    data_interface=pickle.load(data_interface_file)
    model_1=Model(data_interface,target='revenue')
    model_1.train()
    model_1.save_metrics()
    print(model_1.save())
    model_2=Model(data_interface,target='booking_rate')
    model_2.train()
    model_2.save_metrics()
    print(model_2.save())
    data_interface_file.close()


def insights(city_name):
    import pickle
    data_interface_file=open(f'DataInterface_{city_name}.obj','rb')
    data_interface=pickle.load(data_interface_file)
    insights=create_insights(data_interface)
    insight_engine=InsightEngine(data_interface,insights) 
    insight_engine.export()
    data_interface_file.close()
    

def combine(city_name):
    import pickle
    data_interface_file=open(f'DataInterface_{city_name}.obj','rb')
    data_interface=pickle.load(data_interface_file)
    insight_engine=data_interface.get_insight_engine()
    insight_engine.load_model()
    insight_engine.export()
    data_interface_file.close()
    
if __name__ == '__main__':
   city_name='austin'
   etl(city_name)
   modeling(city_name)
   insights(city_name)
   combine(city_name)

            
                
                
                
