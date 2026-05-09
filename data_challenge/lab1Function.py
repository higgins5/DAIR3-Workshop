def sum1(n):
    # sum1(n) computes the sum of 1 + 2 + ... + n 
    total = 0;
    for i in range(1,n+2):
        total = total + i
    return total
#print(sum1(2))

def sum2(n):
    # sun2(n) sums integers squared 
    total = 0;
    for i in range(1,n+1):
        total = total + i**2 
    return total

x = 10
