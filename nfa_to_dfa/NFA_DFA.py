import graphviz
from collections import deque, defaultdict
from graphviz import Digraph
from typing import Set, Tuple, Dict, Any

class NFA:
    def __init__(self, states, alphabet, transitions, start_state, accept_states, epsilon='ε'):
        """
        初始化NFA
        :param states: 状态集合
        :param alphabet: 字母表
        :param transitions: 转移函数
        :param start_state: 初始状态
        :param accept_states: 接受状态集合
        :param epsilon: 空转移符号
        """
        self.states = set(states)
        self.alphabet = set(alphabet)
        self.transitions = transitions
        self.start_state = start_state
        self.accept_states = set(accept_states)
        self.epsilon = epsilon
        
    def get_transition(self, state, symbol):
        """获取状态和符号对应的转移状态集合"""
        return self.transitions.get((state, symbol), set())
    
    def epsilon_closure(self, states_set):
        """
        计算ε闭包
        返回从给定状态集合通过ε转移可达的所有状态集合
        """
        closure = set(states_set)
        stack = list(states_set)
        
        while stack:
            state = stack.pop()
            # 获取当前状态的所有ε转移
            epsilon_states = self.get_transition(state, self.epsilon)
            
            for next_state in epsilon_states:
                if next_state not in closure:
                    closure.add(next_state)
                    stack.append(next_state)
        
        return frozenset(closure)
    
    def move(self, states_set, symbol):
        """
        从给定状态集合通过symbol转移
        """
        result = set()
        for state in states_set:
            result.update(self.get_transition(state, symbol))
        return frozenset(result)

class DFA:
    def __init__(self, states, alphabet, transitions, start_state, accept_states):
        self.states = states
        self.alphabet = alphabet
        self.transitions = transitions
        self.start_state = start_state
        self.accept_states = accept_states

def nfa_to_dfa_with_epsilon(nfa):
    """
    将NFA转换为DFA（子集构造法，支持ε转移）
    """
    # 计算DFA的初始状态（NFA初始状态的ε闭包）
    dfa_start = nfa.epsilon_closure([nfa.start_state])
    
    # 初始化数据结构
    dfa_states = set()
    dfa_accept_states = set()
    dfa_transitions = {}
    
    # 使用队列进行BFS遍历
    queue = deque([dfa_start])
    dfa_states.add(dfa_start)
    
    # 检查初始状态是否为接受(终止)状态
    if any(state in nfa.accept_states for state in dfa_start):
        dfa_accept_states.add(dfa_start)
    
    while queue:
        current_dfa_state = queue.popleft()
        
        # 对每个非空输入符号计算转移
        for symbol in nfa.alphabet:
            if symbol == nfa.epsilon:
                continue
                
            # 1. 从当前DFA状态（NFA状态集合）通过symbol能到达的所有NFA状态
            move_states = nfa.move(current_dfa_state, symbol)
            
            # 如果没有转移，则跳过
            if not move_states:
                continue
            
            # 2. 计算move结果的ε闭包
            next_dfa_state = nfa.epsilon_closure(move_states)
            
            # 记录转移
            dfa_transitions[(current_dfa_state, symbol)] = next_dfa_state
            
            # 如果新状态不在已发现的DFA状态中，则添加到队列
            if next_dfa_state not in dfa_states:
                dfa_states.add(next_dfa_state)
                queue.append(next_dfa_state)
                
                # 检查是否为接受状态
                if any(state in nfa.accept_states for state in next_dfa_state):
                    dfa_accept_states.add(next_dfa_state)
    
    # 创建DFA对象
    dfa = DFA(
        states=dfa_states,
        alphabet=nfa.alphabet - {nfa.epsilon},
        transitions=dfa_transitions,
        start_state=dfa_start,
        accept_states=dfa_accept_states
    )
    
    return dfa

def visualize_nfa_with_epsilon(nfa, filename="nfa_with_epsilon"):
    """
    可视化NFA（支持显示ε转移）
    """
    dot = Digraph(format='png')
    dot.attr(rankdir='LR')
    
    # 添加状态
    for state in nfa.states:
        if state in nfa.accept_states:
            dot.node(str(state), shape='doublecircle')
        else:
            dot.node(str(state))
    
    # 添加初始状态箭头
    dot.node('start', shape='point', style='invis')
    dot.edge('start', str(nfa.start_state))
    
    # 整理转移关系，合并相同起点和终点的多条边
    transitions_dict = defaultdict(list)
    for (from_state, symbol), to_states in nfa.transitions.items():
        for to_state in to_states:
            transitions_dict[(from_state, to_state)].append(str(symbol) if symbol != nfa.epsilon else 'ε')
    
    # 添加转移边
    for (from_state, to_state), symbols in transitions_dict.items():
        label = ", ".join(symbols)
        # 如果是ε转移，用虚线表示
        if 'ε' in symbols and len(symbols) == 1:
            dot.edge(str(from_state), str(to_state), label='ε', style='dashed', color='gray')
        else:
            dot.edge(str(from_state), str(to_state), label=label)
    
    # 渲染
    dot.render(filename, view=False, cleanup=True)
    print(f"NFA图（含ε转移）已保存为 {filename}.png")
    return dot

def visualize_detailed_dfa(dfa, nfa_accept_states=None, filename="dfa_detailed"):
    """
    可视化DFA，显示详细的转换信息
    """
    dot = Digraph(format='png')
    dot.attr(rankdir='LR')
    
    # 为DFA状态创建更友好的标签
    state_labels = {}
    state_names = {}
    
    # 为DFA状态分配简单名称
    for i, dfa_state in enumerate(sorted(dfa.states, key=lambda x: (len(x), sorted(x)))):
        if dfa_state:
            # 将状态集合转换为有序字符串
            sorted_states = sorted(dfa_state)
            state_str = ",".join(sorted_states)
        else:
            state_str = "∅"
        
        # 状态名称
        state_name = f"q{i}"
        state_labels[dfa_state] = state_name
        state_names[dfa_state] = f"{state_name}\n{{{state_str}}}"
    
    # 添加状态
    for dfa_state, label in state_labels.items():
        # 检查是否为接受状态
        is_accept = dfa_state in dfa.accept_states
        node_label = state_names[dfa_state]
        
        # # 高亮显示包含原始NFA接受状态的DFA状态
        # if nfa_accept_states and any(state in nfa_accept_states for state in dfa_state):
        #     node_label += "\n(含接受状态)"
        
        if is_accept:
            dot.node(label, node_label, shape='doublecircle', style='filled', fillcolor='lightblue')
        else:
            dot.node(label, node_label, shape='circle')
    
    # 添加初始状态箭头
    start_label = state_labels[dfa.start_state]
    dot.node('start', shape='point', style='invis')
    dot.edge('start', start_label)
    
    # 整理转移关系
    transitions_by_state = defaultdict(list)
    for (from_state, symbol), to_state in dfa.transitions.items():
        transitions_by_state[(from_state, to_state)].append(str(symbol))
    
    # 添加转移边
    for (from_state, to_state), symbols in transitions_by_state.items():
        from_label = state_labels[from_state]
        to_label = state_labels[to_state]
        label = ", ".join(sorted(symbols))
        dot.edge(from_label, to_label, label=label)
    
    # 渲染
    dot.render(filename, view=False, cleanup=True)
    print(f"详细DFA图已保存为 {filename}.png")
    return dot

def print_nfa_detailed_info(nfa):
    """打印详细的NFA信息"""
    print("=" * 70)
    print("NFA详细信息:")
    print("=" * 70)
    print(f"状态集合: {sorted(nfa.states)}")
    print(f"字母表: {sorted(nfa.alphabet - {nfa.epsilon})} (ε转移符号: '{nfa.epsilon}')")
    print(f"初始状态: {nfa.start_state}")
    print(f"接受状态: {sorted(nfa.accept_states)}")
    
    print("\n转移函数:")
    # 按状态和输入符号排序
    transitions_by_state = defaultdict(lambda: defaultdict(list))
    for (state, symbol), to_states in nfa.transitions.items():
        for to_state in sorted(to_states):
            transitions_by_state[state][to_state].append(str(symbol) if symbol != nfa.epsilon else 'ε')
    
    for state in sorted(transitions_by_state.keys()):
        for to_state in sorted(transitions_by_state[state].keys()):
            symbols = transitions_by_state[state][to_state]
            label = ", ".join(symbols)
            print(f"  δ({state}, {label}) → {to_state}")
    
    # 打印ε闭包信息
    print("\nε闭包计算:")
    for state in sorted(nfa.states):
        closure = nfa.epsilon_closure([state])
        print(f"  ε-closure({state}) = {{{', '.join(sorted(closure))}}}")

def print_dfa_detailed_info(dfa, nfa_accept_states):
    """打印详细的DFA信息"""
    print("\n" + "=" * 70)
    print("转换后的DFA详细信息:")
    print("=" * 70)
    
    # 为DFA状态创建标签
    state_labels = {}
    state_names = {}
    
    for i, dfa_state in enumerate(sorted(dfa.states, key=lambda x: (len(x), sorted(x)))):
        if dfa_state:
            state_str = "{" + ",".join(sorted(dfa_state)) + "}"
        else:
            state_str = "∅"
        state_labels[dfa_state] = f"q{i}"
        state_names[dfa_state] = f"q{i}({state_str})"
    
    print(f"DFA状态数: {len(dfa.states)}")
    print(f"字母表: {sorted(dfa.alphabet)}")
    print(f"初始状态: {state_names[dfa.start_state]}")
    
    # 接受状态
    accept_names = [state_names[s] for s in sorted(dfa.accept_states, key=lambda x: state_names[x])]
    print(f"接受状态: {accept_names}")
    
    # 打印哪些DFA状态包含原始NFA的接受状态
    print("\nDFA状态包含的NFA状态:")
    for dfa_state, name in state_names.items():
        if dfa_state:
            nfa_states = sorted(dfa_state)
            is_accept = any(state in nfa_accept_states for state in dfa_state)
            accept_mark = " (含接受状态)" if is_accept else ""
            print(f"  {name}: {{{', '.join(nfa_states)}}}{accept_mark}")
    
    print("\n转移函数:")
    # 按状态分组
    transitions_by_state = defaultdict(list)
    for (from_state, symbol), to_state in dfa.transitions.items():
        transitions_by_state[from_state].append((symbol, to_state))
    
    for from_state in sorted(transitions_by_state.keys(), key=lambda x: state_names[x]):
        transitions = sorted(transitions_by_state[from_state], key=lambda x: x[0])
        for symbol, to_state in transitions:
            print(f"  δ({state_names[from_state]}, {symbol}) = {state_names[to_state]}")

def example_nfa_with_epsilon_1():
    """
    示例NFA 1: 包含ε转移
    接受语言: a*b*c*
    """
    states = {'q0', 'q1', 'q2', 'q3', 'q4'}
    alphabet = {'a', 'b', 'c', 'ε'}
    
    transitions = {
        ('q0', 'a'): {'q0'},
        ('q0', 'ε'): {'q1'},
        ('q1', 'b'): {'q1'},
        ('q1', 'ε'): {'q2'},
        ('q2', 'c'): {'q2', 'q3'},
        ('q2', 'ε'): {'q4'},
        ('q3', 'c'): {'q3'},
    }
    
    start_state = 'q0'
    accept_states = {'q4'}
    
    return NFA(states, alphabet, transitions, start_state, accept_states)

def example_nfa_with_epsilon_2():
    """
    示例NFA 2: 包含ε转移
    接受语言: (a|b)*abb
    """
    states = {'q0', 'q1', 'q2', 'q3'}
    alphabet = {'a', 'b', 'ε'}
    
    transitions = {
        ('q0', 'a'): {'q0'},
        ('q0', 'b'): {'q0'},
        ('q0', 'ε'): {'q1'},
        ('q1', 'a'): {'q2'},
        ('q2', 'b'): {'q3'},
        ('q3', 'b'): {'q4'},
    }
    
    start_state = 'q0'
    accept_states = {'q4'}
    
    return NFA(states, alphabet, transitions, start_state, accept_states)

def example_nfa_with_epsilon_3():
    """
    示例NFA 3: 更复杂的ε转移示例
    接受语言: a(a|b)*b
    """
    states = {'S', 'A', 'B', 'C', 'D', 'E'}
    alphabet = {'a', 'b', 'ε'}
    
    transitions = {
        ('S', 'a'): {'A'},
        ('A', 'ε'): {'B'},
        ('B', 'a'): {'C'},
        ('B', 'b'): {'C'},
        ('C', 'ε'): {'B', 'D'},
        ('D', 'b'): {'E'},
    }
    
    start_state = 'S'
    accept_states = {'E'}
    
    return NFA(states, alphabet, transitions, start_state, accept_states)

def visualize_conversion_process(nfa, dfa, filename="conversion_process"):
    """
    可视化转换过程，展示关键步骤
    """
    dot = Digraph(format='png')
    dot.attr(rankdir='TB', compound='true')
    
    # 创建子图1: NFA
    with dot.subgraph(name='cluster_nfa') as c:
        c.attr(label='NFA', style='filled', color='lightgrey')
        c.attr(rankdir='LR')
        
        for state in nfa.states:
            if state in nfa.accept_states:
                c.node(f'nfa_{state}', str(state), shape='doublecircle')
            else:
                c.node(f'nfa_{state}', str(state))
        
        # 添加初始状态箭头
        c.node('nfa_start', shape='point', style='invis')
        c.edge('nfa_start', f'nfa_{nfa.start_state}')
        
        # 添加转移边
        for (from_state, symbol), to_states in nfa.transitions.items():
            for to_state in to_states:
                label = 'ε' if symbol == nfa.epsilon else symbol
                style = 'dashed' if symbol == nfa.epsilon else 'solid'
                c.edge(f'nfa_{from_state}', f'nfa_{to_state}', label=label, style=style)
    
    # 创建子图2: DFA
    with dot.subgraph(name='cluster_dfa') as c:
        c.attr(label='DFA', style='filled', color='lightblue')
        c.attr(rankdir='LR')
        
        # 为DFA状态创建标签
        state_labels = {}
        for i, dfa_state in enumerate(sorted(dfa.states, key=lambda x: (len(x), sorted(x)))):
            if dfa_state:
                state_str = "{" + ",".join(sorted(dfa_state)) + "}"
            else:
                state_str = "∅"
            state_labels[dfa_state] = f"q{i}"
            state_name = f"q{i}\n{state_str}"
            
            if dfa_state in dfa.accept_states:
                c.node(f'dfa_q{i}', state_name, shape='doublecircle')
            else:
                c.node(f'dfa_q{i}', state_name)
        
        # 添加初始状态箭头
        start_idx = list(state_labels.keys()).index(dfa.start_state)
        c.node('dfa_start', shape='point', style='invis')
        c.edge('dfa_start', f'dfa_q{start_idx}')
        
        # 添加转移边
        for (from_state, symbol), to_state in dfa.transitions.items():
            from_idx = list(state_labels.keys()).index(from_state)
            to_idx = list(state_labels.keys()).index(to_state)
            c.edge(f'dfa_q{from_idx}', f'dfa_q{to_idx}', label=str(symbol))
    
    # 添加转换箭头
    dot.edge('cluster_nfa', 'cluster_dfa', style='dashed', color='red', constraint='false')
    
    # 渲染
    dot.render(filename, view=False, cleanup=True)
    print(f"转换过程图已保存为 {filename}.png")
    return dot

def simulate_nfa_with_epsilon(nfa, input_string):
    """
    模拟NFA（支持ε转移）对输入字符串的处理
    """
    print(f"\n模拟NFA处理输入字符串: '{input_string}'")
    
    # 初始状态集合是起始状态的ε闭包
    current_states = nfa.epsilon_closure([nfa.start_state])
    print(f"初始状态集合 (ε-closure(start)): {{{', '.join(sorted(current_states))}}}")
    
    for i, symbol in enumerate(input_string):
        if symbol not in nfa.alphabet - {nfa.epsilon}:
            print(f"错误: 符号 '{symbol}' 不在字母表中!")
            return False
        
        # 1. 从当前状态集合通过symbol转移
        move_states = nfa.move(current_states, symbol)
        print(f"\n步骤 {i+1}: 输入符号 '{symbol}'")
        print(f"  move({{{', '.join(sorted(current_states))}}}, {symbol}) = {{{', '.join(sorted(move_states))}}}")
        
        # 2. 计算ε闭包
        current_states = nfa.epsilon_closure(move_states)
        print(f"  ε-closure({{{', '.join(sorted(move_states))}}}) = {{{', '.join(sorted(current_states))}}}")
    
    # 检查是否有状态在接受状态集合中
    is_accepted = any(state in nfa.accept_states for state in current_states)
    print(f"\n最终状态集合: {{{', '.join(sorted(current_states))}}}")
    print(f"是否接受: {'是' if is_accepted else '否'}")
    
    return is_accepted

def simulate_dfa(dfa, input_string):
    """
    模拟DFA对输入字符串的处理
    """
    print(f"\n模拟DFA处理输入字符串: '{input_string}'")
    
    current_state = dfa.start_state
    print(f"初始状态: {current_state}")
    
    for i, symbol in enumerate(input_string):
        if symbol not in dfa.alphabet:
            print(f"错误: 符号 '{symbol}' 不在字母表中!")
            return False
        
        if (current_state, symbol) in dfa.transitions:
            next_state = dfa.transitions[(current_state, symbol)]
            print(f"步骤 {i+1}: δ({current_state}, {symbol}) = {next_state}")
            current_state = next_state
        else:
            print(f"步骤 {i+1}: 从状态 {current_state} 没有对符号 '{symbol}' 的转移")
            return False
    
    is_accepted = current_state in dfa.accept_states
    print(f"最终状态: {current_state}")
    print(f"是否接受: {'是' if is_accepted else '否'}")
    
    return is_accepted

def main():
    """
    主函数：演示支持ε转移的NFA到DFA转换
    """
    print("NFA到DFA的确定化算法（支持ε转移）")
    print("=" * 70)
    
    # 选择示例
    print("请选择要使用的示例NFA:")
    print("1. 简单示例: 接受语言 a*b*c* (含多个ε转移)")
    print("2. 常见示例: 接受语言 (a|b)*abb")
    print("3. 复杂示例: 接受语言 a(a|b)*b")
    
    choice = input("请输入选择 (1, 2 或 3): ").strip()
    
    if choice == '1':
        nfa = example_nfa_with_epsilon_1()
        example_name = "epsilon1"
    elif choice == '2':
        nfa = example_nfa_with_epsilon_2()
        example_name = "epsilon2"
    elif choice == '3':
        nfa = example_nfa_with_epsilon_3()
        example_name = "epsilon3"
    else:
        print("无效选择，使用默认示例1")
        nfa = example_nfa_with_epsilon_1()
        example_name = "epsilon1"
    
    # 打印NFA信息
    print_nfa_detailed_info(nfa)
    
    # 可视化NFA
    print(f"\n正在生成NFA可视化图...")
    visualize_nfa_with_epsilon(nfa, f"nfa_{example_name}")
    
    # 转换为DFA
    print("\n正在执行NFA到DFA的转换（包含ε闭包计算）...")
    dfa = nfa_to_dfa_with_epsilon(nfa)
    
    # 打印DFA信息
    print_dfa_detailed_info(dfa, nfa.accept_states)
    
    # 可视化DFA
    print(f"\n正在生成DFA可视化图...")
    visualize_detailed_dfa(dfa, nfa.accept_states, f"dfa_{example_name}")
    
    # 可视化转换过程
    print(f"\n正在生成转换过程图...")
    visualize_conversion_process(nfa, dfa, f"conversion_{example_name}")
    
    # 测试字符串
    test_strings = []
    if choice == '1':
        test_strings = ['abc', 'aabbcc', 'aaabbbccc', 'aaa', 'bbb', 'ccc', 'ab', 'bc']
    elif choice == '2':
        test_strings = ['abb', 'aabb', 'babb', 'ababb', 'ab', 'abab', 'aaaabb']
    elif choice == '3':
        test_strings = ['ab', 'aab', 'abb', 'aaab', 'abbb', 'aabb', 'abab']
    
    print("\n" + "=" * 70)
    print("字符串测试:")
    print("=" * 70)
    
    for test_str in test_strings:
        print(f"\n测试字符串: '{test_str}'")
        nfa_result = simulate_nfa_with_epsilon(nfa, test_str)
        dfa_result = simulate_dfa(dfa, test_str)
        
        if nfa_result == dfa_result:
            print(f"✓ NFA和DFA结果一致: {'接受' if nfa_result else '拒绝'}")
        else:
            print(f"✗ 错误: NFA和DFA结果不一致!")
            print(f"  NFA: {'接受' if nfa_result else '拒绝'}")
            print(f"  DFA: {'接受' if dfa_result else '拒绝'}")
    
    print("\n" + "=" * 70)
    print("转换完成！")
    print(f"NFA图已保存为: nfa_{example_name}.png")
    print(f"DFA图已保存为: dfa_{example_name}.png")
    print(f"转换过程图已保存为: conversion_{example_name}.png")
    print("=" * 70)
    
    # 显示转换步骤
    print("\n转换过程总结:")
    print("1. 计算NFA初始状态的ε闭包作为DFA初始状态")
    print("2. 对每个DFA状态和输入符号，计算move(T, a) = ∪ δ(p, a) for p in T")
    print("3. 计算ε-closure(move(T, a))得到新的DFA状态")
    print("4. 重复直到没有新状态产生")
    print("5. 包含NFA接受状态的DFA状态标记为DFA接受状态")

if __name__ == "__main__":
    # 安装graphviz: pip install graphviz
    # 还需要安装graphviz软件: https://graphviz.org/download/
    main()