from operator import attrgetter

class Student:
    def __init__(self, name, age, grade):
        self.name = name
        self.age = age
        self.grade = grade

student1 = Student("Alice", 20, "A")
student2 = Student("Bob", 22, "B")

name_age_getter = attrgetter("name", "age", "name.find")
print(name_age_getter(student1))  # Output: ('Alice', 20)
print(name_age_getter(student2))  # Output: ('Bob', 22)