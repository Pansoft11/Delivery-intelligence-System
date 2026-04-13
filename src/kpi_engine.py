def calculate_kpi(df):
    rft=df['RFT'].mean()*100
    otd=df['OTD'].mean()*100
    return {'RFT %':round(rft,2),'OTD %':round(otd,2)}