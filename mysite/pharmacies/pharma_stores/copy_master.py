import shutil

def make_copies(input_file, num_copies):
    for i in range(num_copies):
        output_file = f'A{i+1}.csv'
        shutil.copy(input_file, output_file)

    print(f'{num_copies} копий успешно созданы.')

make_copies('a1.csv', 10)
