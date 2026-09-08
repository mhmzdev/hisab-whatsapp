# Accounts — shop

## Assets — money accounts (setup adds yours below)
account assets:cash    ; DEFAULT
account assets:bank:meezan

## Assets — customers who owe the shop (udhaar)
account assets:receivable

## Assets — staff advances
account assets:staff:advance

## Liabilities — suppliers the shop owes
account liabilities:payable

## Equity
account equity:opening             ; starting balances — "balance <account> <amount>" posts here
account equity:transfer            ; the bare third posting on a move between two money accounts

## Income
account income:sales
account income:other

## Expenses
account expenses:stock             ; goods bought for resale
account expenses:rent
account expenses:salaries
account expenses:utilities:electricity
account expenses:utilities:gas
account expenses:utilities:internet
account expenses:transport         ; deliveries, fuel, rickshaw
account expenses:supplies          ; bags, packaging, cleaning
account expenses:repairs
account expenses:fees              ; bank, license, tax
account expenses:other

## Added at setup
account liabilities:payable:metro
account liabilities:payable:ali traders
account assets:staff:advance:bilal

## Recurring — periodic rules; budget and forecast read these

~ monthly from 2026-09  rent  ; budget:
    expenses:rent                           PKR 40,000.00
    assets:cash

~ monthly from 2026-09  salaries  ; budget:
    expenses:salaries                       PKR 60,000.00
    assets:cash
