'use strict';

var moduleListApp = angular.module('moduleListApp', []);

var types = ["module", "class", "function"];

moduleListApp.controller(
  'ModuleListCtrl',
  function ($scope, $http) {
    $http.get('apidoc.json').success(function (data) {
      $scope.modules = data;
      $scope.module = "";

      $scope.sortDict = function (obj) {
        var result = [];
        for (name in obj) 
          result.push([name, obj[name]]);
        result.sort(function (item0, item1) { 
          var t0 = types.indexOf(item0[1].type);
          var t1 = types.indexOf(item1[1].type);
          var n0 = item0[1].name;
          var n1 = item1[1].name;
          return t0 < t1 ? -1 : t0 > t1 ?  1 : n0 < n1 ? -1 : n0 > n1 ?  1 : 0;
        });
        return result;
      };
    });
});

//------------------------------------------------------------------------------

