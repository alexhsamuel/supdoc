"use strict";

var filterObj = function (obj, predicate) {
  var result = {};
  for (name in obj) 
    if (predicate(name, obj))
      result[name] = obj;
  return result;
}

