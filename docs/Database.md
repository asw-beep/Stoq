# Tables

## users

id
email
password_hash
role
created_at

---

## stocks

id
symbol
name
sector

---

## historical_prices

id
stock_id
date

open
high
low
close

volume

---

## forecasts

id

stock_id

forecast_date

model

predicted_price

confidence

---

## news_articles

id

title

content

source

published_at

---

## sentiment_scores

id

article_id

sentiment

confidence

---

## portfolios

id

user_id

name

created_at

---

## holdings

id

portfolio_id

stock_id

shares

purchase_price