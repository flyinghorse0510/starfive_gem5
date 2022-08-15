#!/bin/bash

tgtDir="${PWD}/src/mem/ruby"

allCommits=$(git log --reverse --pretty=format:"%h" --since='Aug 25 2021' --until='Aug 15 2022' public/stable ${tgtDir})
for cmmit in $allCommits; do
    # echo $cmmit
    git cherry-pick $cmmit
done