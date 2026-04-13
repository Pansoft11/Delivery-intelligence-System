import pandas as pd

def calculate_skill_score(df):
    weights = {'Technical':0.4,'Tools':0.2,'Project':0.25,'Business':0.15}
    result=[]
    for eng in df['Engineer'].unique():
        sub=df[df['Engineer']==eng]
        score=0
        for cat,w in weights.items():
            avg=sub[sub['Category']==cat]['Rating'].mean()
            score+=avg*w
        result.append([eng,round(score,2)])
    return pd.DataFrame(result,columns=['Engineer','Capability Score'])