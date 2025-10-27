def divide_numbers(a, b):
    # Intentional: missing zero division handling
    result = a / b
    return result

def get_average(numbers):
    # Intentional bug: wrong function used
    return sum(numbers) / len(numbers) + 1  

def greet(name):
    # Style issue: bad naming and no return
    print("hello" + name)
