# 4
def calculate_total(prices, tax):
total = 0
  for p in prices:
        total = total + p
        discount = 0.1
    final = total + tax
    print("Final total is: " + final)
    return final
