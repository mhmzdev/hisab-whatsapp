# Rules — keyword => account. First match wins; longer keywords first. The agent appends what it learns.

## food
food, meal, lunch, dinner, breakfast, khana, biryani, karahi, pizza, burger, foodpanda, restaurant, dhaba, naan, roti, shawarma, daal => expenses:food:meal
snack, snacks, chips, biscuit, biscuits, samosa, pakora, coffee, cafe, latte, chai, tea, juice, cold drink, ice cream => expenses:food:snacks
grocery, groceries, sabzi, fruit, fruits, milk, doodh, eggs, anday, bread, bakery, imtiaz, carrefour, metro => expenses:food:groceries

## transport
petrol, fuel, diesel, careem, uber, bykea, indrive, yango, rickshaw, ride, bus, train, toll, parking, m-tag => expenses:transport

## utilities
bijli, electricity, kesc, k-electric, iesco, lesco, wapda => expenses:utilities:electricity
gas, sui gas, ssgc, sngpl => expenses:utilities:gas
internet, wifi, ptcl, nayatel, stormfiber => expenses:utilities:internet
mobile, data, jazz, zong, telenor, ufone, easyload, package => expenses:utilities:mobile

## other
netflix, spotify, youtube, icloud, subscription => expenses:subscriptions
doctor, medicine, dawai, pharmacy, hospital, lab test => expenses:health
gift, tohfa, shadi => expenses:gifts
sadqa, sadaqah, zakat, donation, charity, khairat => expenses:donations
