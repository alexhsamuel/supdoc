"use strict"

var ObjectModule = angular.module('ObjectModule', [])

ObjectModule.config(
  function () {
  })

ObjectModule.controller(
  'ObjectController', 
  function ($scope) {
  	$scope.id = 'ObjectController'

    /* Names of direct submodules.  */
    $scope.$watch(
      'api',
      function (api) {
        $scope.submoduleNames = api && api.modules ? Object.keys(api.modules) : []
      })

  })

