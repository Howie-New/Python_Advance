from operator import itemgetter

xiaoA = {
    "name": "Xiao A",
    "age": 25,
    "city": "Beijing"
}

xiaoB = {
    "name": "Xiao B",
    "age": 30,
    "city": "Shanghai"
}

name_age = itemgetter("name", "age")  
name_city = itemgetter("name", "city")

print(name_age(xiaoA))  # Output: ('Xiao A', 25)
print(name_city(xiaoB))  # Output: ('Xiao B', 'Shanghai')

Fibonacci_Sequence = [1,1,2,3,5,8,13,21,34,55,89]

first_last = itemgetter(0, -1)
first , last= first_last(Fibonacci_Sequence)
print(f"Fibonacci Sequence 11 num  : first is {first} and last is {last}")