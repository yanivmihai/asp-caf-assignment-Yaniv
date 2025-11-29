#ifndef TREE_H
#define TREE_H

#include <unordered_map>
#include <map>
#include <string>
#include <utility>

#include "tree_record.h"

class Tree {
public:
    // Canonical storage for tree records
    const std::map<std::string, TreeRecord> records;

    // Construct from unordered_map: copy into sorted map
    explicit Tree(const std::unordered_map<std::string, TreeRecord>& recs)
        : records(recs.begin(), recs.end()) {}

    // Construct directly from a map if ever needed
    explicit Tree(const std::map<std::string, TreeRecord>& recs)
        : records(recs) {}

    std::map<std::string, TreeRecord>::const_iterator record(const std::string& key) const {
        return records.find(key);
    }
};

#endif // TREE_H
