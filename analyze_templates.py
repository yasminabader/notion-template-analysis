import pandas as pd
import sqlite3
import re

# Read csv 
data = pd.read_csv("notion_templates.csv")

# Since downlaod count is a string, convert it to a number
def to_number(val):
    if pd.isna(val) or str(val).strip() == '': return None
    val = str(val).replace('+', '').strip()
    if 'K' in val: return float(val.replace('K', '')) * 1000
    if 'M' in val: return float(val.replace('M', '')) * 1000000
    try: return float(val)
    except: return None


# Since price is a string, convert to number as well
def to_price(val):
    if pd.isna(val) or val == 'Free': return 0.0
    try: return float(str(val).replace('$', ''))
    except: return None

# Since categories and features are strings, convert to numbers
def count_items(val):
    if pd.isna(val) or val == '': return 0
    return len(str(val).split(','))

# Since creator template count is a string, convert to number
def to_creator_num(val):
    if pd.isna(val): return None
    m = re.search(r'(\d+)', str(val))
    return int(m.group(1)) if m else None



# Apply the functions above to their respective columns. This is the final step to make sure everything is a number and not a string 
data['download_count']         = data['downloads'].apply(to_number)
data['price_dollars']          = data['price'].apply(to_price)
data['num_features']           = data['features'].apply(count_items)
data['num_categories']         = data['categories'].apply(count_items)
data['num_screenshots']        = data['preview_image_count']
data['creator_template_count'] = data['creator_template_count'].apply(to_creator_num)


db = sqlite3.connect("notion_templates.db")
data.to_sql("templates", db, if_exists="replace", index=False)
print("Loaded into SQLite\n")


# The analysis part 

# How many downloads do Free vs Paid templates have on average?
print("\n1. Free vs Paid")
q1 = pd.read_sql_query("""SELECT CASE WHEN is_free=1 THEN 'Free' ELSE 'Paid' END AS type, COUNT(*) AS num_templates, ROUND(AVG(download_count)) AS avg_downloads FROM templates WHERE download_count IS NOT NULL GROUP BY is_free ORDER BY avg_downloads DESC""", db)
print(q1.to_string(index=False))
print(f"  → Free gets {q1.iloc[0]['avg_downloads']/q1.iloc[1]['avg_downloads']:.1f}x more downloads than paid")

# What is the best price point to drive downloads?
print("\n2. Best price points (paid only)")
q2 = pd.read_sql_query("""SELECT CASE WHEN price_dollars<=1 THEN 'Under $1' WHEN price_dollars<=3 THEN '$1-$3' WHEN price_dollars<=5 THEN '$3-$5' WHEN price_dollars<=10 THEN '$5-$10' WHEN price_dollars<=20 THEN '$10-$20' ELSE 'Over $20' END AS price_range, COUNT(*) AS num_templates, ROUND(AVG(download_count)) AS avg_downloads FROM templates WHERE is_free=0 AND download_count IS NOT NULL GROUP BY price_range ORDER BY avg_downloads DESC""", db)
print(q2.to_string(index=False))
print(f"  → '{q2.iloc[0]['price_range']}' gets {q2.iloc[0]['avg_downloads']/q2.iloc[-1]['avg_downloads']:.1f}x more downloads than '{q2.iloc[-1]['price_range']}'")

# How many categories should a template creator list?
print("\n3. How many categories to list in?")
q3 = pd.read_sql_query("""SELECT CASE WHEN num_categories<=2 THEN '1-2' WHEN num_categories<=4 THEN '3-4' WHEN num_categories<=6 THEN '5-6' WHEN num_categories<=8 THEN '7-8' ELSE '9+' END AS category_count, COUNT(*) AS num_templates, ROUND(AVG(download_count)) AS avg_downloads FROM templates WHERE download_count IS NOT NULL GROUP BY category_count ORDER BY avg_downloads DESC""", db)
print(q3.to_string(index=False))
print(f"  → {q3.iloc[0]['category_count']} categories gets {q3.iloc[0]['avg_downloads']/q3.iloc[-1]['avg_downloads']:.1f}x more downloads than {q3.iloc[-1]['category_count']}")

# Does adding Notion features help? (AI, formulas, charts, etc)
print("\n4. Does adding Notion features help?")
q4 = pd.read_sql_query("""SELECT num_features, COUNT(*) AS num_templates, ROUND(AVG(download_count)) AS avg_downloads FROM templates WHERE download_count IS NOT NULL GROUP BY num_features ORDER BY avg_downloads DESC""", db)
print(q4.to_string(index=False))

# How many screenshots should a template creator put on the listing?
print("\n5. How many screenshots?")
q5 = pd.read_sql_query("""SELECT num_screenshots, COUNT(*) AS num_templates, ROUND(AVG(download_count)) AS avg_downloads FROM templates WHERE download_count IS NOT NULL GROUP BY num_screenshots ORDER BY avg_downloads DESC""", db)
print(q5.to_string(index=False))
print(f"  → {int(q5.iloc[0]['num_screenshots'])} screenshots gets {q5.iloc[0]['avg_downloads']/q5.iloc[-1]['avg_downloads']:.1f}x more downloads than {int(q5.iloc[-1]['num_screenshots'])}")

# Does a bigger creator catalog help? (Like if a creator has 100 templates, does that help?)
print("\n6. Does a bigger creator catalog help?")
q6 = pd.read_sql_query("""SELECT CASE WHEN creator_template_count<=5 THEN '1-5 templates' WHEN creator_template_count<=15 THEN '6-15 templates' WHEN creator_template_count<=30 THEN '16-30 templates' WHEN creator_template_count<=100 THEN '31-100 templates' ELSE '100+ templates' END AS creator_size, COUNT(*) AS num_templates, ROUND(AVG(download_count)) AS avg_downloads FROM templates WHERE download_count IS NOT NULL AND creator_template_count IS NOT NULL GROUP BY creator_size ORDER BY avg_downloads DESC""", db)
print(q6.to_string(index=False))
print(f"  → '{q6.iloc[0]['creator_size']}' gets {q6.iloc[0]['avg_downloads']/q6.iloc[-1]['avg_downloads']:.1f}x more downloads than '{q6.iloc[-1]['creator_size']}'")

# Top 10 templates in my scraped data by download count
print("\n7. Top 10 by downloads")
q7 = pd.read_sql_query("""SELECT title, price, download_count, num_features, num_categories, num_screenshots FROM templates WHERE download_count IS NOT NULL ORDER BY download_count DESC LIMIT 10""", db)
print(q7.to_string(index=False))

# Hidden gems (high rating, low downloads) - write about this
print("\n8. Hidden gems (high rating, low downloads)")
q8 = pd.read_sql_query("""SELECT title, price, rating, download_count, num_categories FROM templates WHERE rating>=4.9 AND download_count<1000 AND download_count IS NOT NULL ORDER BY download_count ASC LIMIT 10""", db)
print(q8.to_string(index=False))

# Paid templates that went viral (5K+ downloads is my personal benchmark for viral) 
print("\n9. Paid templates that went viral (5K+ downloads)")
q9 = pd.read_sql_query("""SELECT title, price, download_count, num_categories, num_features FROM templates WHERE is_free=0 AND download_count>5000 ORDER BY download_count DESC""", db)
print(q9.to_string(index=False))

# Most downloaded free vs paid
print("\n10. Most downloaded free vs paid")
q10 = pd.read_sql_query("""SELECT CASE WHEN is_free=1 THEN 'Free' ELSE 'Paid' END AS type, title, price, download_count FROM templates WHERE (is_free=1 AND download_count=(SELECT MAX(download_count) FROM templates WHERE is_free=1)) OR (is_free=0 AND download_count=(SELECT MAX(download_count) FROM templates WHERE is_free=0))""", db)
print(q10.to_string(index=False))



# print Descriptive stats
print("\n=== DESCRIPTIVE STATS ===")
print(f"Total templates scraped: {len(data)}")
print(f"Avg rating: {data['rating'].mean():.2f}")
print(f"Median rating: {data['rating'].median():.2f}")
print(f"Avg downloads: {data['download_count'].mean():,.0f}")
print(f"Median downloads: {data['download_count'].median():,.0f}")
print(f"Max downloads: {data['download_count'].max():,.0f}")
print(f"Min downloads: {data['download_count'].min():,.0f}")
print(f"Free templates: {data['is_free'].sum()} ({data['is_free'].mean()*100:.0f}%)")
print(f"Paid templates: {(~data['is_free']).sum()} ({(~data['is_free']).mean()*100:.0f}%)")
paid = data[data['is_free']==False]['price_dollars']
print(f"Avg price (paid only): ${paid.mean():.2f}")
print(f"Median price (paid only): ${paid.median():.2f}")
print(f"Templates with 5K+ downloads: {(data['download_count'] >= 5000).sum()}")
print(f"Median creator catalog size: {data['creator_template_count'].median():.0f} templates")
print(f"Avg creator catalog size: {data['creator_template_count'].mean():.0f} templates")
print("\nTop 5 most common categories:")
print(data['categories'].str.split(',').explode().str.strip().value_counts().head(5))
print("\nMost common features:")
print(data['features'].str.split(',').explode().str.strip().value_counts())

db.close()
print("\nFinished Running")
