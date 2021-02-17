#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import numpy as np
import seaborn as sns
from urllib.request import urlopen
from bs4 import BeautifulSoup


# In[2]:


import time
import datetime
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary


# In[3]:


#conda install -c conda-forge geckodriver
binary = FirefoxBinary(r'C:\Program Files\Mozilla Firefox\firefox.exe')
driver = webdriver.Firefox(firefox_binary=binary)


# In[4]:


url = "https://www.hapag-lloyd.com/en/online-business/schedules/vessel-tracing.html"
driver.get(url)


# In[5]:


time.sleep(6) #sleep 6 seconds enough time for web to load
driver.find_element_by_id("accept-recommended-btn-handler").click() # accept all cookies pop up


# In[6]:


time.sleep(5)
driver.find_element_by_xpath("//img[@id='ext-gen131']").click() #click dropdown arrow
time.sleep(5)
mainlineOptions = driver.find_elements_by_class_name('x-combo-list-item')
mainlineOptionsList = [optship.text for optship in mainlineOptions]


# In[7]:


#loop through web schedule which is a table and create a list
def built_table_list(souptable, vesselName):
    atlanticStList = ['al', 'ct', 'de', 'dc', 'fl', 'ga', 'la', 'me', 'md', 
                      'ma', 'ms','nh', 'nj', 'ny', 'nc', 'ri', 'sc', 'tx', 'va']
    atlanticStFound = False
    scheduleList = []
    tableRows = souptable.find_all('tr')
    for tr in tableRows:
        td = tr.find_all('td')
        row = [i.text for i in td]
        lenrow = len(row)
        if (lenrow == 11 or lenrow == 12):
            city = row[1] if lenrow == 11 else row[2]
            eaDateTime = "{0} {1}".format(row[3], row[4]) if lenrow == 11 else "{0} {1}".format(row[4], row[5])
            edDateTime = "{0} {1}".format(row[7], row[8]) if lenrow == 11 else "{0} {1}".format(row[8], row[9])
            cityState = city.split(",")
            if len(cityState) == 2:
                city = cityState[0].strip()
                state = cityState[1].strip()
                if state.lower() in atlanticStList:
                    atlanticStFound = True
            else:
                state = ""
            scheduleList.append([vesselName, city, state, eaDateTime, edDateTime])
    if atlanticStFound:
        return scheduleList
    else:
        return []


# In[12]:


scheduleNames = ['vessel','city','state','estimated_arrival','estimated_departure']
df = pd.DataFrame([], columns=scheduleNames)


# In[17]:


skipShip = True
for mainlineVessel in mainlineOptionsList:
    # If program crashes, check what was the last one selected on the browser
    # and uncomment next 4 lines below
    #if skipShip:
    #    if mainlineVessel == 'HANSA RENDSBURG':
    #        skipShip = False
    #    continue
    if mainlineVessel == '...':
        continue
    try:
        inputMainlineElement = driver.find_element_by_xpath("//input[@id='ext-gen129']")
    except Exception as e:
        try:
            inputMainlineElement = driver.find_element_by_xpath("//input[@id='ext-gen157']")
        except Exception as e:
            try:
                inputMainlineElement = driver.find_element_by_xpath("//input[@id='ext-gen138']")
            except Exception as e:
                try:
                    inputMainlineElement = driver.find_element_by_xpath("//input[@id='ext-gen146']")
                except Exception as e:
                    # close and reopen browser. go to next vessel
                    driver.close()
                    driver = webdriver.Firefox(firefox_binary=binary)
                    driver.get(url)
                    time.sleep(6) #sleep 6 seconds enough time for web to load
                    driver.find_element_by_id("accept-recommended-btn-handler").click() # accept all cookies pop up
                    time.sleep(5)
                    driver.find_element_by_xpath("//img[@id='ext-gen131']").click() #click dropdown arrow
                    time.sleep(5)
                    continue
    inputMainlineElement.send_keys(Keys.CONTROL + "a");
    inputMainlineElement.send_keys(Keys.DELETE);
    inputMainlineElement.send_keys(mainlineVessel)
    time.sleep(5)
    inputMainlineElement.send_keys(Keys.ENTER)
    time.sleep(5)
    driver.find_element_by_id("schedules_vessel_tracing_f:hl24").click() # click find
    time.sleep(10)
    newPgSource = driver.page_source
    soup = BeautifulSoup(newPgSource, 'lxml')
    scheduleVesselTracing = soup.find(id='schedules_vessel_tracing_f:hl68')
    if not scheduleVesselTracing:
        continue
    tableResultsList = built_table_list(scheduleVesselTracing, mainlineVessel)
    if tableResultsList:
        #print(mainlineVessel)
        df2 = pd.DataFrame(tableResultsList, columns=scheduleNames)
        df = pd.concat([df, df2])


# In[18]:


driver.close()


# In[ ]:


def organize_route(rl):
    list1 = []
    list2 = []
    freq = 1
    skiptoNum = 0
    routeCreated = False
    routeList = rl.split(',')
    for routeIndx, city in enumerate(routeList):
#        print(city)
        if routeIndx < skiptoNum:
            continue
#        print("{0} in {1}".format(city, list1))
        if city in list1:
            indices = [i1 for i1, x1 in enumerate(list1) if x1 == city]
            if indices:
                beforeCityIndx = indices[len(indices)-1]
                lenlist1 = len(list1[beforeCityIndx:])
#                print("{0} == {1}".format(routeList[routeIndx:routeIndx+lenlist1],list1[beforeCityIndx:]))
                if routeList[routeIndx:routeIndx+lenlist1] == list1[beforeCityIndx:]:
#                    print("#### {0} - {1} - {2}".format(skiptoNum,freq,list1[:beforeCityIndx]))
                    if list1[:beforeCityIndx]:
                        list2.append((freq,','.join(list1[:beforeCityIndx])))
                        freq = 1
                    freq += 1
                    skiptoNum = routeIndx+lenlist1
                    list1 = routeList[routeIndx:routeIndx+lenlist1]
                    routeCreated = True
                    
            if not routeCreated:
                if skiptoNum:
#                    print(">>>> {0} - {1} - {2}".format(skiptoNum,freq,list1))
                    list2.append((freq,','.join(list1)))
                    list1 = []
                    skiptoNum = 0
                    freq = 1
                routeCreated = False
                list1.append(city)
#                print("no route found {0}".format(list1))
        else:
            if skiptoNum:
#                print("**** {0} - {1} - {2}".format(skiptoNum,freq,list1))
                list2.append((freq,','.join(list1)))
                list1 = []
                skiptoNum = 0
                freq = 1
            routeCreated = False
            list1.append(city)
#            print("else new {0}".format(list1))

    list2.append((freq,','.join(list1)))
    return list2


# In[ ]:


df2 = df.groupby('vessel')['city'].apply(','.join).reset_index().rename(columns={'city':'all_cities_row'})


# In[ ]:


df2['routes'] = df2['all_cities_row'].apply(organize_route)


# In[ ]:


df3 = df.merge(df2[['vessel','routes']],left_on='vessel',right_on='vessel')


# In[ ]:


df3['departing_to'] = df3.groupby('vessel')['city'].shift(-1)


# In[19]:


todayDate = datetime.datetime.now()
df3.to_csv("hapag_lloyd_{0}.csv".format(todayDate.strftime("%Y-%m-%d")), index=False)


# In[ ]:




