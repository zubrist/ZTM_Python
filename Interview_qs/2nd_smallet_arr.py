# find the second smallest element in array


def secondSmallest(arr):
    first = second = float('inf')
    
    for num in arr:
        if num < first:
            second = first
            first = num
        
        elif first < num < second:
            second = num
    
    return second



arr = [12,23,11,45,53,2]
result = secondSmallest(arr)
print(result)            