class Action:
    def pre_commit(self):
        """Do some action on file, in durable but revertible form (e.g. if your
        action is deleting a file, don't delete it here but just rename to some
        temporary name and (preferably) make some durable log that you did so in
        case your process will be restarted and you are asked to commit all that
        you haven't committed yet).
        If something is incorrect while performing precommit, just rollback your
        changes (if you've already done something) and raise an error -
        if you were part of a distributed transaction, the transaction will be
        rolled back.
        If all was good on precommit, just exit from the method.
        Then you will get either commit() or rollback() request depending on the
        outcome of other participants of a transaction"""

    def commit(self):
        """Finally materialize the changes done on pre_commit(). Typically, no
        rollback is possible after it is done. E.g. if your action was about
        deleting a file, here you finally remove the temporarily renamed copy."""

    def rollback(self):
        """Revert changes done on process(). Can be done only after pre_commit()."""


def process_actions_atomically(actions):
    actions_for_rollback_on_error = []
    need_rollback = False
    for action in actions:
        print(f'Precommitting {action}')
        try:
            """#we append before actually calling pre_commit() in order to allow this action 
            to be rolled back too if it failed in the mid of precommit"""
            actions_for_rollback_on_error.append(action)
            action.pre_commit()
            # should_fail = input("Simulate exception (Y/N)?")
            # if should_fail.lower() == "y":
            #     raise RuntimeError("Asked to fail")
        except BaseException as e:
            print(f"Action {action} failed due to {e}, rolling back everything")
            need_rollback = True
            break
    if need_rollback:
        print("Performing rollback")
        # we rollback most recent actions first
        for action in reversed(actions_for_rollback_on_error):
            try:
                action.rollback()
            except BaseException as e:
                print(f"Failed to rollback action {action} due to {e}, skipping it")
    else:
        print("All actions precommitted fine, committing")
        for action in actions:
            try:
                action.commit()
            except BaseException as e:
                print(f"Failed to commit action {action} due to {e}, skipping it")
    print("Done")
