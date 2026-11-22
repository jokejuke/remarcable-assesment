# checkout Specification

## Purpose

Lets logged-in users place orders for in-stock products without overselling, and keeps an accurate record of what was bought and at what price.

## Requirements

### Requirement: Orders contain items
An order SHALL belong to one user and contain one or more items. Each item SHALL reference one product with a quantity of at least 1, and each product SHALL appear at most once per order.

#### Scenario: Order with two items
- **WHEN** a shopper orders 2 units of product 7 and 1 unit of product 3
- **THEN** one order is created with two items

### Requirement: Prices are captured at purchase
Each order item SHALL store the unit price at the time of purchase, and the order SHALL store its total as the sum of quantity times unit price. Later price changes SHALL NOT change existing orders.

#### Scenario: Price changes later
- **WHEN** a product bought at 4900 cents is later repriced to 5900 cents
- **THEN** the existing order still shows 4900 cents per unit and the original total

### Requirement: Stock is decremented atomically
Placing an order SHALL reduce each product's stock by the ordered quantity. Concurrent orders SHALL never reduce stock below zero or sell more units than were available.

#### Scenario: Race for the last unit
- **WHEN** two orders for the last unit of a product are placed at the same time
- **THEN** exactly one succeeds, the other fails as out of stock, and stock ends at 0

### Requirement: Orders are all-or-nothing
If any item in an order lacks enough stock, the system SHALL create no order and change no stock.

#### Scenario: One item short
- **WHEN** a shopper orders products 7 (in stock) and 3 (stock 0)
- **THEN** no order is created and product 7's stock is unchanged

### Requirement: Out-of-stock response lists every failing product
When an order fails on stock, the API SHALL respond 409 and list every product that lacked enough stock.

#### Scenario: Two items short
- **WHEN** an API order includes products 3 and 9, both with insufficient stock
- **THEN** the response is 409 and lists both 3 and 9

### Requirement: Order input is validated at the API
The API SHALL reject an order with 400 when it has no items, a quantity below 1, an unknown product, or the same product twice.

#### Scenario: Zero quantity
- **WHEN** an API order includes an item with quantity 0
- **THEN** the response is 400 and no stock changes

#### Scenario: Unknown product
- **WHEN** an API order references a product id that does not exist
- **THEN** the response is 400

#### Scenario: Duplicate product
- **WHEN** an API order lists product 7 twice
- **THEN** the response is 400

### Requirement: Checkout requires login
Only logged-in users SHALL be able to place orders.

#### Scenario: Anonymous order
- **WHEN** an unauthenticated client posts an order to the API
- **THEN** it receives 401 and no order is created

### Requirement: Order history is private
Users SHALL only see their own orders. Another user's order SHALL be reported as not found.

#### Scenario: Another user's order
- **WHEN** shopper A requests shopper B's order by id
- **THEN** the response is 404

### Requirement: Order records are kept
Orders SHALL NOT be editable by users. Products and users that have orders SHALL NOT be deletable.

#### Scenario: Deleting a user with orders
- **WHEN** an administrator deletes a user who has placed orders
- **THEN** the deletion is refused
