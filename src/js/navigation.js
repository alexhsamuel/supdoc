var navigation = angular.module('navigation', [])

navigation.controller(
  'NavigationController', 
  function ($scope, $routeParams) {
    $scope.fqname = $routeParams.fqname ? $routeParams.fqname.split('/').join('.') : '(none)'
    $scope.templateUrl = $routeParams.templateUrl
    $scope.$watch(
      function () { return $routeParams.fqname },
      function (fqname) { console.log(fqname) })
  })

