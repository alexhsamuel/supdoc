"use strict"

angular.module('ObjectModule', [])

.config(
  function () {
  })

.controller(
  'ObjectController', 
  function ($scope) {
  	console.log('ObjectController creation')
  	$scope.api = $scope.getApi($scope.fqname)

  	$scope.submoduleNames = function () {
		console.log('submoduleNames')
		var modules = $scope.api.modules
		console.log(modules)
		return modules ? Object.keys(modules) : []
  	}
  })
