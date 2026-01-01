# Acme Corp Monolith Application
# A sample e-commerce platform for demonstrating Tessera decomposition

A Django-based e-commerce monolith with:
- User management & authentication
- Product catalog
- Shopping cart & checkout
- Order processing
- Payment integration
- Inventory management
- Notifications (email, SMS)
- Reporting & analytics

## Structure

```
acme-monolith/
├── acme/
│   ├── settings/
│   ├── urls.py
│   └── wsgi.py
├── users/           # User management bounded context
├── products/        # Product catalog bounded context
├── cart/            # Shopping cart bounded context
├── orders/          # Order processing bounded context
├── payments/        # Payment bounded context
├── inventory/       # Inventory bounded context
├── notifications/   # Notification bounded context
└── analytics/       # Reporting bounded context
```

## Recommended Decomposition

Tessera will identify these as separate microservices:
1. **User Service** - Authentication, profiles, preferences
2. **Catalog Service** - Products, categories, search
3. **Cart Service** - Shopping cart, sessions
4. **Order Service** - Order lifecycle, fulfillment
5. **Payment Service** - Stripe integration, invoicing
6. **Inventory Service** - Stock levels, warehouses
7. **Notification Service** - Email, SMS, push notifications
