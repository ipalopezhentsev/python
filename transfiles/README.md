Library that models transactionary file system and utilities that are built on top of it.
Transactionary means that first we create list of actions to perform, and each action
could be reverted if other actions go wrong. I.e. when working with files it doesn't delete
file as soon as told and uses temporary copies.