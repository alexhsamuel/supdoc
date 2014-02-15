"use strict"

angular.module('Routing', ['ngRoute']) 

.config(
  function ($locationProvider, $routeProvider) {
    $locationProvider.html5Mode(true)
    $routeProvider
      .when('/apyi', { templateUrl: '/title.html' })
      .when('/apyi/:fqname', { templateUrl: '/object.html' }) 
      .otherwise({ templateUrl: '/error.html' }) 
  })

.controller(
  'NavigationController', 
  function ($scope, $location, $routeParams) {
    $scope.$watch(
      function () { return $routeParams.fqname },
      function (fqname) { $scope.fqname = fqname })
    $scope.$watch(
      function () { return $scope.fqname },
      function (fqname) { if (typeof fqname !== 'undefined') $location.path('/apyi/' + fqname) })
  })

