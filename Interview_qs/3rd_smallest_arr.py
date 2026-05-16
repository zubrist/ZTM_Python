# find the 3rd smallest element in the array



def thirdSmallest(arr):
    first = second = third = float ('inf')
    
    for num in arr:
        if num < first:
            third = second
            second = first
            first = num
        elif num < second:
            third = second
            second = num
        
        elif num < third:
            third = num
    return third        



if __name__ == "__main__":
    arr = [23,54,11,56,88,59]
    print(thirdSmallest(arr))                    