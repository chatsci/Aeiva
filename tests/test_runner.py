from aeiva.runner.runner import Runner

def multiply_by_two(ctx):
    num = ctx.get('number', 1)
    ctx.update({'multiply_by_two_result': num * 2})
    return ctx

def multiply_by_three(ctx):
    num = ctx.get('number', 1)
    ctx.update({'multiply_by_three_result': num * 3})
    return ctx

def add_numbers(ctx):
    result_two = ctx.get('multiply_by_two_result', 0)
    result_three = ctx.get('multiply_by_three_result', 0)
    ctx.update({'add_result': result_two + result_three})
    return ctx

def subtract_numbers(ctx):
    result_two = ctx.get('multiply_by_two_result', 0)
    result_three = ctx.get('multiply_by_three_result', 0)
    ctx.update({'subtract_result': result_two - result_three})
    return ctx

def sum_results(ctx):
    add_res = ctx.get('add_result', 0)
    subtract_res = ctx.get('subtract_result', 0)
    ctx.update({'sum_results': add_res + subtract_res})
    return ctx

if __name__ == "__main__":
    ctx = {'number': 10}
    runner = Runner()
    node1 = runner.add_operator('multiply_by_two', multiply_by_two)
    node2 = runner.add_operator('multiply_by_three', multiply_by_three)
    node3 = runner.add_operator('add_numbers', add_numbers)
    node4 = runner.add_operator('subtract_numbers', subtract_numbers)
    node5 = runner.add_operator('sum_results', sum_results)

    # Link the nodes according to the DAG.
    runner.link_operators(node1, node3)
    runner.link_operators(node1, node4)
    runner.link_operators(node2, node3)
    runner.link_operators(node2, node4)
    runner.link_operators(node3, node5)
    runner.link_operators(node4, node5)

    # Run the operations.
    runner(ctx)
    print(ctx)
