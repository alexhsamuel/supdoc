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
    $scope.nav = {
      fqname: $routeParams.fqname || '',
      templateUrl: $routeParams.templateUrl
    }

    $scope.$watch(
      function () { 
        return $routeParams.fqname 
      },
      function (fqname) { 
        console.log(fqname)
        $scope.nav.fqname = fqname 
      })
    $scope.$watch(
      function () { 
        return $scope.nav.fqname 
      },
      function (fqname) { 
        if (typeof fqname !== 'undefined') 
          $location.path('/apyi/' + fqname) 
      })
  })

