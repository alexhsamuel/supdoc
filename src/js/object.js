"use strict"

angular.module('Object', ['ngRoute'])

.config(
  function () {
    console.log("Object.config")
  })

.controller(
  'ObjectController', 
  function ($scope, $routeParams) {
    $scope.fqname = $routeParams.fqname
  })

