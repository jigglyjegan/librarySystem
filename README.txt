BT2102 Group 11 Assignment 1

Team members:
Khoo Wu Chuan A0217391E
Ong Shen Quan, Jaryl A0222643M
Angela Natasha Wibowo A0223014B
Jeyakumar Jegan A0217456B
Teng Yu-Hsiang A0219943W
Yasalapu Siva Sai Theja A0218140U


This assignment aims to create an Integrated Library System that can manage book borrowing, returning and other related operations efficiently and effectively.This web based application has the following functionalities:

- Sign-up for member users
- Log-in for admin and member users
- Book Search (Simple) : Search books by titles
- Book Search (Advanced) : Search books using filters (Author, Category, Year of Publication)
- Borrowing of Books through Book Search function
- Reservation of Books through Book Search function
- Manage Books: Return, Extend current borrowings and Cancel and Convert reservations to borrowings
- Fines: Check total fine amount and pay them with credit/debit card

Administrative Function:
Display all borrowings currently in the system including overdue ones
Display all reservations currently in the system
Display all users with unpaid fines along with fine amounts

*Important*
Run pip install -r requirements.txt to ensure all dependencies have been installed
Change the SQL connections information to your system's database information
Import books.json into the mongodb using mongoimport --db library --collection books books.json

Administrative users created in the backend:

user: admin1
password: password

user: admin2
password: password

user: admin3
password: password

SQL Script library.sql contains 10 sample books for testing (book id 1 -10), trying to borrow and reserve books that are not of these sample books will not work since the books are not in the mysql database. In order to make them work books need to be inserted into the mysql database. 