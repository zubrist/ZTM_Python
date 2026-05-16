
def third_largest(arr):
    
    first = second = third = float('-inf')
    
    for num in arr:
        if num > first:
            third = second
            second = first
            first = num
        
        elif num > second:
            third = second
            second = num
        
        elif num > third:
            third = num 
            
    return third


arr = [23,43,11,56,34,78]
result = third_largest(arr)
print(result)           