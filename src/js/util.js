"use strict";

var values = function (obj) {
  var result = [];
  for (name in obj)
    result.push(obj[name]);
  return result;
}

var items = function (obj) {
  var result = [];
  for (name in obj) 
    result.push([name, obj[name]]);
  return result;
}

var filterObj = function (obj, predicate) {
  var result = {};
  for (var key in obj) {
    var value = obj[key];
    if (predicate(key, value))
      result[key] = value;
  }
  return result;
}

