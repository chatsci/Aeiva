# test_analyze_gui.py

from api import analyze_gui

def test_analyze_gui_macos():
    # Test 1: Retrieve all GUI elements
    print("Test 1: Retrieve all GUI elements")
    result = analyze_gui()
    if 'error' in result:
        print("Error:", result['error'])
    else:
        elements = result.get('elements', [])
        print(f"Total elements found: {len(elements)}")
        for elem in elements[:5]:  # Print first 5 elements
            print(f"Name: {elem.get('name')}, Role: {elem.get('role')}")
            print("---")
    print("\n")

    # Test 2: Retrieve elements with target_text
    target_text = 'Submit'
    print(f"Test 2: Retrieve elements with target_text='{target_text}'")
    result = analyze_gui(target_text=target_text)
    if 'error' in result:
        print("Error:", result['error'])
    else:
        elements = result.get('elements', [])
        print(f"Total elements found with target_text='{target_text}': {len(elements)}")
        for elem in elements:
            print(f"Name: {elem.get('name')}, Role: {elem.get('role')}")
            print("---")
    print("\n")

    # Test 3: Retrieve elements with role
    role = 'button'
    print(f"Test 3: Retrieve elements with role='{role}'")
    result = analyze_gui(role=role)
    if 'error' in result:
        print("Error:", result['error'])
    else:
        elements = result.get('elements', [])
        print(f"Total elements found with role='{role}': {len(elements)}")
        for elem in elements[:5]:  # Print first 5 elements
            print(f"Name: {elem.get('name')}, Role: {elem.get('role')}")
            print("---")
    print("\n")

    # Test 4: Retrieve elements with target_text and role
    target_text = 'OK'
    role = 'button'
    print(f"Test 4: Retrieve elements with target_text='{target_text}' and role='{role}'")
    result = analyze_gui(target_text=target_text, role=role)
    if 'error' in result:
        print("Error:", result['error'])
    else:
        elements = result.get('elements', [])
        print(f"Total elements found with target_text='{target_text}' and role='{role}': {len(elements)}")
        for elem in elements:
            print(f"Name: {elem.get('name')}, Role: {elem.get('role')}")
            print("---")
    print("\n")

if __name__ == "__main__":
    test_analyze_gui_macos()