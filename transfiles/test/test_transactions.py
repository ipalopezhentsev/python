import transfiles.transactions as transactions
from unittest.mock import Mock, create_autospec, MagicMock


def mock_action_not_failing_anywhere():
    action = create_autospec(transactions.Action)
    return action


def mock_action_failing_on_precommit():
    action = create_autospec(transactions.Action)
    action.pre_commit = Mock(side_effect=RuntimeError("fail!"))
    return action


def mock_action_failing_on_precommit_and_rollback():
    action = create_autospec(transactions.Action)
    action.pre_commit = Mock(side_effect=RuntimeError("fail precommit!"))
    action.rollback = Mock(side_effect=RuntimeError("fail rollback!"))
    return action


def mock_action_failing_on_commit():
    action = create_autospec(transactions.Action)
    action.commit = Mock(side_effect=RuntimeError("fail on commit!"))
    return action


class TestTransactions:
    def test_process_actions_atomically_happy_path(self):
        """tests all is good when all actions finish fine"""
        good_action1 = mock_action_not_failing_anywhere()
        good_action2 = mock_action_not_failing_anywhere()
        transactions.process_actions_atomically([good_action1, good_action2])

        good_action1.pre_commit.assert_called_once()
        good_action2.pre_commit.assert_called_once()
        good_action1.commit.assert_called_once()
        good_action2.commit.assert_called_once()
        good_action1.rollback.assert_not_called()
        good_action2.rollback.assert_not_called()

    def test_rollbacks_itself_if_precommit_fails(self):
        bad_action = mock_action_failing_on_precommit()
        transactions.process_actions_atomically((bad_action,))

        bad_action.pre_commit.assert_called_once()
        bad_action.commit.assert_not_called()
        bad_action.rollback.assert_called_once()

    def test_calls_rollback_in_reverse_order(self):
        manager = MagicMock()
        good_action1 = mock_action_not_failing_anywhere()
        bad_action = mock_action_failing_on_precommit()
        good_action2 = mock_action_not_failing_anywhere()
        good_action1_name = "good_action1"
        manager.attach_mock(good_action1, good_action1_name)
        bad_action_name = "bad_action"
        manager.attach_mock(bad_action, bad_action_name)

        transactions.process_actions_atomically(
            [good_action1, bad_action, good_action2])

        """it should fail on bad action, roll it back, 
        then roll back good_action1.
        good_action2 shouldn't be touched at all"""
        good_action1.pre_commit.assert_called_once()
        good_action1.commit.assert_not_called()
        good_action1.rollback.assert_called_once()

        bad_action.pre_commit.assert_called_once()
        bad_action.commit.assert_not_called()
        bad_action.rollback.assert_called_once()

        good_action2.pre_commit.assert_not_called()
        good_action2.commit.assert_not_called()
        good_action2.rollback.assert_not_called()

        """now test it calls rollbacks in correct sequence 
        (first bad_action, then good_action1)"""
        idx_good_action1_rollback = None
        idx_bad_action_rollback = None
        for idx, call in enumerate(manager.mock_calls):
            if call[0] == f"{good_action1_name}.rollback":
                idx_good_action1_rollback = idx
            elif call[0] == f"{bad_action_name}.rollback":
                idx_bad_action_rollback = idx
        assert idx_good_action1_rollback is not None
        assert idx_bad_action_rollback is not None
        assert idx_bad_action_rollback < idx_good_action1_rollback

    def test_failure_on_rollback_doesnt_prevent_other_rollbacks(self):
        good_action = mock_action_not_failing_anywhere()
        bad_action = mock_action_failing_on_precommit_and_rollback()
        transactions.process_actions_atomically([good_action, bad_action])

        good_action.pre_commit.assert_called_once()
        bad_action.pre_commit.assert_called_once()
        # will fail:
        bad_action.rollback.assert_called_once()
        # but it shouldn't preclude to rollback good action:
        good_action.rollback.assert_called_once()
        good_action.commit.assert_not_called()
        bad_action.commit.assert_not_called()

    def test_failure_on_commit_doesnt_prevent_other_commits(self):
        good_action = mock_action_not_failing_anywhere()
        bad_action = mock_action_failing_on_commit()
        transactions.process_actions_atomically([bad_action, good_action])

        bad_action.pre_commit.assert_called_once()
        good_action.pre_commit.assert_called_once()
        # will fail:
        bad_action.commit.assert_called_once()
        # but should not prevent calling commit on good action:
        good_action.commit.assert_called_once()
        """
        Q: shouldn't bad_action.rollback be called too?
        A: I think no, it would violate rule that transaction is atomic.
        In most cases target action will be done on pre_commit() already, 
        so at worst we'll have some temporary leftover for being able to revert.
        """
