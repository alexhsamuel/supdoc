'use strict';

var moduleListApp = angular.module('moduleListApp', []);

moduleListApp.controller(
  'ModuleListCtrl',
  function ($scope, $http) {
    $http.get('apidoc.json').success(function (data) {
      $scope.modules = data;
      $scope.module = "";
    });
});

