def find_2nd_largest(arr):
    first=second= float('-inf')
    
    for num in arr:
        if num > first:
            second = first
            first = num
        elif first > num > second:
            second = num
    
    return second


arr = [2,5, 67,23,55,5]

result = find_2nd_largest(arr)

print(result)        
