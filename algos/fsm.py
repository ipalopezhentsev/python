from typing import List, TypeVar, Dict, Set, NamedTuple

"""Implementation of generic finite state machine,
inspired by Yandex Praktikum https://www.youtube.com/watch?v=LWA43vTeFGQ ,
but generified and also implemented generation of FSMs for searching subtrings inside a string"""

Symbol = TypeVar("Symbol")
State = TypeVar("State")


class CheckResult(NamedTuple):
    passed: bool
    final_state: State
    comment: str


class FSM:
    """Finite state machine"""
    def __init__(self, alphabet: Set[Symbol], start_state: State,
                 final_states: Set[State], jump_table: Dict[State, Dict[Symbol, State]]):
        """
        alphabet - list of allowed symbols in the language this FSE specifies.
        start_state - starting state of automaton
        final_states - collection of states that are treated as 'final' or 'successful' - meaning
        that if after processing the whole input string the state machine is in one of these states
        the input string is considered to be accepted by the state machine.
        jump_table - mapping of current state to mapping of a new symbol encountered while being in
        this state to the new state to which machine should transfer after encountering this symbol
        """
        self.alphabet = alphabet
        self.start_state = start_state
        self.final_states = final_states
        self.jump_table = jump_table

    def accepts(self, input_string: List[Symbol]) -> CheckResult:
        """
        Takes input_string and checks whether it is recognised by this state machine (i.e. if
        after traversing all symbols in the input_string the final state is one of the final states).
        Returns tuple where first parameter is status of successful recognition, second parameter
        means final state of the machine after traversing the whole input_string and the third.
        """
        cur_state = self.start_state
        for sym in input_string:
            if sym not in self.alphabet:
                return CheckResult(False, cur_state, f"Symbol {sym} is not in our alphabet")
            jumps_from_cur_state = self.jump_table.get(cur_state, None)
            if jumps_from_cur_state is None:
                return CheckResult(False, cur_state, f"No jumps found from state {cur_state}")
            new_state = jumps_from_cur_state.get(sym, None)
            if new_state is None:
                return CheckResult(False, cur_state, f"No jump found from {cur_state} and symbol {sym}")
            cur_state = new_state
        return CheckResult(cur_state in self.final_states, cur_state, "")


def generate_jump_subtable(source_symbols: List[Symbol], target_state: State) -> Dict[Symbol, State]:
    res = {}
    for sym in source_symbols:
        res[sym] = target_state
    return res


all_lowercase_letters = "qazwsxedcrfvtgbyhnujmikolp"
all_letters = all_lowercase_letters.upper() + all_lowercase_letters


def generate_fsm_for_substring_search(string: str) -> FSM:
    if string is None or string == "":
        state = "q0"
        return FSM(all_letters, state, {state}, {state: generate_jump_subtable(all_letters, state)})
    first_letter = string[0]
    all_letters_wo_starting = all_letters.replace(first_letter, "")
    jump_table = {"q1":
                      generate_jump_subtable(all_letters_wo_starting, "q1") |
                      {first_letter: "q2"}}
    state_num = 2
    for sym in string[1:]:
        all_letters_wo_current = all_letters.replace(sym, "")
        jump_table[f"q{state_num}"] = generate_jump_subtable(all_letters_wo_current, "q1") | \
                                      {sym: f"q{state_num + 1}"}
        state_num += 1
    jump_table[f"q{state_num}"] = generate_jump_subtable(all_letters, f"q{state_num}")
    return FSM(all_letters, "q1", {f"q{state_num}"}, jump_table)


def main():
    fsm_starts_with_1 = FSM({'0', '1'}, "q0", {"q1"},
                            {
                                "q0": {"1": "q1"},
                                "q1": {"0": "q1",
                                       "1": "q1"}
                            })
    assert fsm_starts_with_1.accepts("10111000").passed
    assert not fsm_starts_with_1.accepts("0110").passed

    fsm_substring = generate_fsm_for_substring_search("Ilya")
    assert not fsm_substring.accepts("").passed
    """
       | I  | l  | y  | a
    q1 | q2 | q1 | q1 | q1
    q2 | q1 | q3 | q1 | q1
    q3 | q1 | q1 | q4 | q1
    q4 | q1 | q1 | q1 | q5
    q5 | q5 | q5 | q5 | q5
    """
    assert fsm_substring.accepts("Ilya").passed
    assert fsm_substring.accepts("qIlya").passed
    assert fsm_substring.accepts("IlyaW").passed
    assert fsm_substring.accepts("qIlyaW").passed
    assert not fsm_substring.accepts("qIqlqyqaq").passed

    fsm_substring_empty = generate_fsm_for_substring_search("")
    assert fsm_substring_empty.accepts("").passed  # "" contains ""
    assert fsm_substring_empty.accepts("Ilya").passed  # "Ilya" contains ""


if __name__ == "__main__":
    main()
