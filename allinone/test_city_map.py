def load_city_map():
    city_map = {}
    try:
        with open('city_map.txt', 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) == 3:
                    location, x, y = parts
                    city_map[location] = (int(x), int(y))
                else:
                    print(f"Ignoring invalid line: {line}")
        print("City map loaded successfully")
    except Exception as e:
        print(f"Error loading city map: {str(e)}")
    return city_map

def test_city_map():
    city_map = load_city_map()
    print("City Map:")
    for location, coordinates in city_map.items():
        print(f"{location}: {coordinates}")

if __name__ == "__main__":
    test_city_map()