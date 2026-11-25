# Purity – Home & Lifestyle E-commerce Website

Purity is a customized full-stack home and lifestyle storefront built with **HTML, CSS, JavaScript, Python, Flask, and SQLite**. It includes a responsive multi-page storefront, product browsing, a persistent shopping cart, contact and newsletter forms, and a checkout demonstration.

This project is a customized derivative of the open-source MNML project by KanikaTomar18. The upstream source is available at https://github.com/KanikaTomar18/MNML. Please review and follow the upstream repository's license and attribution requirements when sharing or publishing your version.

## Features

### Storefront
- Responsive multi-page storefront with a sage-green visual theme
- Product catalog: New In, Objects, Living, and Archive
- Shopping cart with quantity management and browser `localStorage`
- Product search and category filtering
- FAQ, contact, shipping, and returns pages
- Newsletter signup

### Checkout demonstration
- Customer contact and delivery details
- UPI, credit/debit card, digital wallet, and Cash on Delivery choices
- Order summary and order confirmation
- Orders recorded by the Flask API in SQLite
- **Demo only:** no real payment is processed and no card or UPI credentials are collected

### Backend
- Flask REST API
- SQLite database created automatically on first run (`purity.db`)
- Product catalog, contact messages, newsletter signups, and order logging
- Server-side validation and product-price calculation

## Technology stack
- Python 3
- Flask
- SQLite
- HTML5, CSS3, JavaScript (ES6)
- Bootstrap 5

## Project structure

```text
Purity/
├── app.py
├── build.py
├── requirements.txt
├── Procfile
├── README.md
├── index.html
├── new-in.html
├── objects.html
├── living.html
├── archive.html
├── contact.html
├── faq.html
├── shipping.html
├── returns.html
├── checkout.html
├── style.css
├── cart.css
├── checkout.css
├── cart.js
└── checkout.js
```

## Run locally (Windows PowerShell)

Open a terminal in the folder containing `app.py`, then run:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000 in your browser.

On first launch, the app creates and seeds `purity.db` with sample products. Delete this database file to reset the local sample data.

## Important payment note

The checkout page is a portfolio demonstration only. Payment method selection is simulated; no money is charged. To accept real payments, integrate a payment provider such as Razorpay using its official server-side checkout flow. Never store raw card details in this application.

## Upstream attribution

Customized from **MNML** by **KanikaTomar18**: https://github.com/KanikaTomar18/MNML
